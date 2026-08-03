"""Watchlist JSON store + summary mapper."""

from __future__ import annotations

from pathlib import Path

from app.configs.settings import Settings
from app.schemas.evidence import Evidence, EvidenceBundle
from app.schemas.phase0 import Phase0Result, Phase0Status
from app.schemas.report import InvestmentThesis, Scorecard, ThesisClaim
from app.schemas.watchlist import ListKind, summary_from_phase0
from app.services import watchlist_store as store


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        google_api_key=None,
        watchlist_path=tmp_path / "watchlist.json",
    )


def test_put_and_get_membership(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    m = store.put_membership(["nvda", "aapl"], ["msft", "NVDA"], s)
    assert m.held == ["NVDA", "AAPL"]
    assert m.watched == ["MSFT"]  # NVDA held wins
    assert store.get_membership(s).held == ["NVDA", "AAPL"]


def test_add_remove_ticker(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    store.put_membership([], ["AAPL"], s)
    store.add_ticker("nvda", ListKind.HELD, s)
    m = store.get_membership(s)
    assert m.held == ["NVDA"]
    assert m.watched == ["AAPL"]
    store.remove_ticker("aapl", s)
    assert store.get_membership(s).watched == []


def test_bulk_remove_subset(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    store.put_membership(["NVDA", "AAPL"], ["MSFT", "GOOG"], s)
    result = store.bulk_remove(["aapl", "MSFT", "ZZZZ"], s)
    assert result.affected == ["AAPL", "MSFT"]
    assert result.skipped_not_found == ["ZZZZ"]
    m = store.get_membership(s)
    assert m.held == ["NVDA"]
    assert m.watched == ["GOOG"]


def test_bulk_move_held_watched_and_noop(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    store.put_membership(["NVDA"], ["AAPL", "MSFT"], s)
    result = store.bulk_move(["AAPL", "NVDA", "FAKE"], ListKind.HELD, s)
    assert result.affected == ["AAPL"]
    assert result.skipped_noop == ["NVDA"]
    assert result.skipped_not_found == ["FAKE"]
    m = store.get_membership(s)
    assert m.held == ["NVDA", "AAPL"]
    assert m.watched == ["MSFT"]

    back = store.bulk_move(["NVDA", "AAPL"], ListKind.WATCHED, s)
    assert set(back.affected) == {"NVDA", "AAPL"}
    m = store.get_membership(s)
    assert m.held == []
    assert set(m.watched) == {"MSFT", "NVDA", "AAPL"}


def test_bulk_remove_invalid_ticker_raises(tmp_path: Path) -> None:
    from app.schemas.ticker import InvalidTickerError

    s = _settings(tmp_path)
    store.put_membership(["NVDA"], [], s)
    try:
        store.bulk_remove(["NVDA", "not a ticker!!!"], s)
        raise AssertionError("expected InvalidTickerError")
    except InvalidTickerError:
        pass


def test_summary_from_phase0_maps_fields() -> None:
    result = Phase0Result(
        ticker="NVDA",
        status=Phase0Status.OK,
        evidence=EvidenceBundle(
            ticker="NVDA",
            items=[
                Evidence(
                    id="ev1",
                    type="financial",
                    source="yahoo",
                    confidence=0.9,
                    data={},
                )
            ],
            conflicts=[],
        ),
        thesis=InvestmentThesis(
            ticker="NVDA",
            thesis="Growth remains strong on AI demand for data centers worldwide.",
            claims=[ThesisClaim(text="Claim", evidence_ids=["ev1"])],
        ),
        scorecard=Scorecard(
            ticker="NVDA",
            growth_score=80.0,
            value_score=40.0,
            risk_score=55.0,
        ),
        cache_hit=True,
        request_id="req-1",
    )
    summary = summary_from_phase0(result, list_kind=ListKind.HELD)
    assert summary.ticker == "NVDA"
    assert summary.growth_score == 80.0
    assert summary.conflict_count == 0
    assert summary.cache_hit is True
    assert summary.thesis_one_liner is not None
    assert "Growth remains" in summary.thesis_one_liner


def test_upsert_summary_round_trip(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    store.put_membership(["NVDA"], [], s)
    result = Phase0Result(
        ticker="NVDA",
        status=Phase0Status.ERROR,
        evidence=None,
        thesis=None,
        error_message="boom",
        cache_hit=False,
        request_id="r2",
    )
    summary = summary_from_phase0(result, list_kind=ListKind.HELD)
    store.upsert_summary(summary, s)
    rows = store.get_summaries(s)
    assert len(rows) == 1
    assert rows[0].status == Phase0Status.ERROR
    assert rows[0].error_message == "boom"

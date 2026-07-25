"""Watchlist service refresh with mocked Phase0."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.configs.settings import Settings
from app.schemas.evidence import Evidence, EvidenceBundle
from app.schemas.phase0 import Phase0Result, Phase0Status
from app.schemas.report import InvestmentThesis, Scorecard, ThesisClaim
from app.schemas.watchlist import ListKind
from app.services import watchlist_store as store
from app.services.watchlist_service import refresh_batch, refresh_ticker


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        google_api_key=None,
        watchlist_path=tmp_path / "watchlist.json",
    )


def _ok_result(ticker: str) -> Phase0Result:
    return Phase0Result(
        ticker=ticker,
        status=Phase0Status.OK,
        evidence=EvidenceBundle(
            ticker=ticker,
            items=[
                Evidence(
                    id="ev1",
                    type="financial",
                    source="yahoo",
                    confidence=0.9,
                    data={},
                )
            ],
        ),
        thesis=InvestmentThesis(
            ticker=ticker,
            thesis=f"{ticker} looks solid.",
            claims=[ThesisClaim(text="ok", evidence_ids=["ev1"])],
        ),
        scorecard=Scorecard(ticker=ticker, growth_score=70.0, risk_score=40.0),
        cache_hit=False,
        request_id=f"req-{ticker}",
    )


def test_refresh_ticker_persists_summary(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    store.put_membership(["NVDA"], [], s)
    summary = refresh_ticker(
        "nvda",
        app_settings=s,
        research_fn=lambda t, **k: _ok_result(t),
    )
    assert summary.growth_score == 70.0
    assert summary.list_kind == ListKind.HELD
    rows = store.get_summaries(s)
    assert rows[0].request_id == "req-NVDA"


def test_refresh_unknown_ticker_raises(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    with pytest.raises(LookupError):
        refresh_ticker("AAPL", app_settings=s, research_fn=lambda t, **k: _ok_result(t))


def test_refresh_batch_caps(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    store.put_membership(
        ["T1", "T2", "T3"],
        ["T4", "T5"],
        s,
    )
    # Use valid ticker formats
    store.put_membership(["AAA", "BBB", "CCC"], ["DDD", "EEE"], s)
    resp = refresh_batch(
        max_tickers=2,
        app_settings=s,
        research_fn=lambda t, **k: _ok_result(t),
        max_workers=2,
    )
    assert len(resp.refreshed) == 2
    assert len(resp.skipped) == 3

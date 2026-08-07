"""Thesis dashboard generator (T1 — injected workers, no network)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.configs.settings import Settings
from app.schemas.financials import FinancialMetrics
from app.schemas.thesis import (
    FrameworkId,
    ThesisGenerationStatus,
    ThesisTicker,
)
from app.schemas.watchlist import ListKind
from app.services import thesis_store, watchlist_store as store
from app.services.thesis_frameworks import scorecards_for
from app.services.thesis_service import (
    EMPTY_UNIVERSE_MSG,
    generate_thesis_dashboard,
)

NOW = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        watchlist_path=tmp_path / "w.json",
        source_cache_dir=tmp_path / "sources",
        phase0_cache_dir=tmp_path / "phase0",
        thesis_store_path=tmp_path / "thesis.json",
    )


def _row(ticker: str, kind: ListKind, **metric_overrides) -> ThesisTicker:
    metrics = FinancialMetrics(ticker=ticker, **metric_overrides)
    return ThesisTicker(
        ticker=ticker,
        list_kind=kind.value,  # type: ignore[arg-type]
        frameworks=scorecards_for(metrics),
        sources_used=["yahoo"],
    )


def test_empty_universe_yields_empty_message(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    store.put_membership([], [], s)
    dash = generate_thesis_dashboard(app_settings=s, now=NOW)
    assert dash.universe_count == 0
    assert dash.empty_message == EMPTY_UNIVERSE_MSG
    assert dash.generation_status == ThesisGenerationStatus.COMPLETE
    assert thesis_store.get_latest_dashboard(s) is not None


def test_generate_builds_rows_held_first(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    store.put_membership(["NVDA"], ["AAPL", "MSFT"], s)

    def worker(ticker: str, kind: ListKind) -> ThesisTicker:
        return _row(ticker, kind, current_ratio=2.5, debt_to_equity=0.4)

    dash = generate_thesis_dashboard(app_settings=s, worker_fn=worker, now=NOW)
    assert dash.universe_count == 3
    assert dash.tickers_considered == 3
    assert [t.ticker for t in dash.tickers] == ["NVDA", "AAPL", "MSFT"]
    assert dash.tickers[0].list_kind == "held"
    assert dash.frameworks == [FrameworkId.GRAHAM, FrameworkId.FINANCIAL_STRENGTH]
    assert dash.generation_status == ThesisGenerationStatus.COMPLETE
    # Persisted for GET.
    latest = thesis_store.get_latest_dashboard(s)
    assert latest is not None
    assert latest.universe_count == 3


def test_worker_failure_is_gap_not_fatal(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    store.put_membership(["NVDA", "FAIL"], [], s)

    def worker(ticker: str, kind: ListKind) -> ThesisTicker:
        if ticker == "FAIL":
            raise RuntimeError("boom")
        return _row(ticker, kind)

    dash = generate_thesis_dashboard(app_settings=s, worker_fn=worker, now=NOW)
    assert [t.ticker for t in dash.tickers] == ["NVDA"]
    assert dash.generation_status == ThesisGenerationStatus.PARTIAL
    assert any("FAIL" in g for g in dash.gaps)


def test_row_gaps_propagate_to_dashboard(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    store.put_membership(["NVDA"], [], s)

    def worker(ticker: str, kind: ListKind) -> ThesisTicker:
        row = _row(ticker, kind)
        row.gaps = [f"{ticker}: sec_xbrl unavailable (Timeout)"]
        return row

    dash = generate_thesis_dashboard(app_settings=s, worker_fn=worker, now=NOW)
    assert dash.generation_status == ThesisGenerationStatus.PARTIAL
    assert any("sec_xbrl" in g for g in dash.gaps)


def test_no_fundamentals_row_has_null_scores(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    store.put_membership(["NVDA"], [], s)

    def worker(ticker: str, kind: ListKind) -> ThesisTicker:
        return _row(ticker, kind)  # empty metrics

    dash = generate_thesis_dashboard(app_settings=s, worker_fn=worker, now=NOW)
    row = dash.tickers[0]
    assert all(card.score is None for card in row.frameworks)


def test_dashboard_always_carries_disclaimer(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    store.put_membership([], [], s)
    dash = generate_thesis_dashboard(app_settings=s, now=NOW)
    assert dash.disclaimer

"""Thesis dashboard generator (T1–T3 — injected workers, no network)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from app.configs.settings import Settings
from app.schemas.financials import FinancialMetrics, StatementSummary
from app.schemas.thesis import (
    FrameworkId,
    ThesisGenerationStatus,
    ThesisTicker,
    ThesisVerdict,
)
from app.schemas.watchlist import ListKind
from app.services import thesis_store, watchlist_store as store
from app.services.thesis_frameworks import scorecards_for
from app.services.thesis_service import (
    EMPTY_UNIVERSE_MSG,
    build_thesis_ticker,
    generate_thesis_dashboard,
)

NOW = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        watchlist_path=tmp_path / "w.json",
        source_cache_dir=tmp_path / "sources",
        phase0_cache_dir=tmp_path / "phase0",
        thesis_store_path=tmp_path / "thesis.json",
        thesis_insight_mode="deterministic",
        thesis_quarter_days=90,
        thesis_snapshot_ring_size=8,
    )


def _row(ticker: str, kind: ListKind, **metric_overrides) -> ThesisTicker:
    metrics = FinancialMetrics(ticker=ticker, **metric_overrides)
    return ThesisTicker(
        ticker=ticker,
        list_kind=kind.value,  # type: ignore[arg-type]
        frameworks=scorecards_for(metrics),
        sources_used=["yahoo"],
    )


def _rich_metrics() -> FinancialMetrics:
    return FinancialMetrics(
        ticker="NVDA",
        eps_trailing=5.0,
        trailing_pe=10.0,
        earnings_growth=0.10,
        total_cash=200.0,
        total_debt=80.0,
        market_cap=100.0,
        current_ratio=2.8,
        debt_to_equity=0.4,
        free_cash_flow=10.0,
        profit_margin=0.2,
        return_on_equity=0.18,
        balance_sheet=StatementSummary(total_liabilities=50.0),
        cash_flow=StatementSummary(operating_cashflow=20.0),
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
        return _row(ticker, kind)

    dash = generate_thesis_dashboard(app_settings=s, worker_fn=worker, now=NOW)
    row = dash.tickers[0]
    assert all(card.score is None for card in row.frameworks)


def test_dashboard_always_carries_disclaimer(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    store.put_membership([], [], s)
    dash = generate_thesis_dashboard(app_settings=s, now=NOW)
    assert dash.disclaimer


def test_build_ticker_attaches_monitoring_and_baseline_snapshot(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    with patch(
        "app.services.thesis_service._merged_fundamentals",
        return_value=(_rich_metrics(), ["yahoo"], []),
    ):
        row = build_thesis_ticker(
            "NVDA",
            ListKind.HELD,
            app_settings=s,
            force_refresh=False,
            now=NOW,
        )
    assert row.monitoring is not None
    assert row.monitoring.current is not None
    assert row.monitoring.current.verdict == ThesisVerdict.NO_CHANGE
    assert "baseline" in row.monitoring.current.evidence[0]
    assert row.monitoring.current.narrative
    assert row.advisor is not None
    assert row.advisor.conclusion_label
    assert row.advisor.provider == "deterministic"
    assert 0.0 <= row.advisor.confidence <= 1.0
    assert thesis_store.get_latest_snapshot("NVDA", app_settings=s) is not None


def test_force_refresh_appends_even_within_quarter(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    with patch(
        "app.services.thesis_service._merged_fundamentals",
        return_value=(_rich_metrics(), ["yahoo"], []),
    ):
        build_thesis_ticker(
            "NVDA", ListKind.HELD, app_settings=s, force_refresh=False, now=NOW
        )
        build_thesis_ticker(
            "NVDA",
            ListKind.HELD,
            app_settings=s,
            force_refresh=False,
            now=NOW + timedelta(days=1),
        )
        assert len(thesis_store.get_snapshots("NVDA", app_settings=s)) == 1
        build_thesis_ticker(
            "NVDA",
            ListKind.HELD,
            app_settings=s,
            force_refresh=True,
            now=NOW + timedelta(days=2),
        )
        assert len(thesis_store.get_snapshots("NVDA", app_settings=s)) == 2

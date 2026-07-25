"""Minimum fundamentals checklist for 2C.3 Yahoo-fatal soften."""

from __future__ import annotations

from app.schemas.financials import FinancialMetrics, PeriodMetric, StatementSummary
from app.schemas.fundamentals_minimum import (
    MINIMUM_FUNDAMENTALS_FIELD_PATHS,
    has_minimum_fundamentals,
    missing_minimum_fundamentals,
)


def _full_snapshot() -> FinancialMetrics:
    bs = StatementSummary(
        as_of="2025-12-31",
        total_revenue=100.0,
        total_assets=500.0,
        total_liabilities=200.0,
        total_cash=50.0,
        total_debt=80.0,
    )
    return FinancialMetrics(
        ticker="AAPL",
        gross_margin=0.4,
        operating_margin=0.3,
        total_debt=80.0,
        total_cash=50.0,
        eps_trailing=6.5,
        earnings_history=[PeriodMetric(period="2025Q4", value=1.5)],
        balance_sheet=bs,
        cash_flow=StatementSummary(as_of="2025-12-31", operating_cashflow=10.0),
    )


def test_minimum_paths_are_editable_frozenset() -> None:
    assert isinstance(MINIMUM_FUNDAMENTALS_FIELD_PATHS, frozenset)
    assert "balance_sheet" in MINIMUM_FUNDAMENTALS_FIELD_PATHS
    assert "balance_sheet.total_revenue" in MINIMUM_FUNDAMENTALS_FIELD_PATHS
    assert "eps_trailing" in MINIMUM_FUNDAMENTALS_FIELD_PATHS
    assert "pe_ratio" not in MINIMUM_FUNDAMENTALS_FIELD_PATHS
    assert "forward_pe" not in MINIMUM_FUNDAMENTALS_FIELD_PATHS
    assert "eps_forward" not in MINIMUM_FUNDAMENTALS_FIELD_PATHS


def test_none_snapshot_missing_all() -> None:
    missing = missing_minimum_fundamentals(None)
    assert missing == sorted(MINIMUM_FUNDAMENTALS_FIELD_PATHS)
    assert has_minimum_fundamentals(None) is False


def test_empty_metrics_missing_required() -> None:
    snap = FinancialMetrics(ticker="AAPL")
    missing = missing_minimum_fundamentals(snap)
    assert "gross_margin" in missing
    assert "balance_sheet" in missing
    assert "earnings_history" in missing
    assert has_minimum_fundamentals(snap) is False


def test_empty_earnings_history_not_enough() -> None:
    snap = _full_snapshot()
    snap.earnings_history = []
    assert "earnings_history" in missing_minimum_fundamentals(snap)


def test_full_snapshot_satisfies_minimum() -> None:
    snap = _full_snapshot()
    assert missing_minimum_fundamentals(snap) == []
    assert has_minimum_fundamentals(snap) is True


def test_nested_balance_sheet_gap() -> None:
    snap = _full_snapshot()
    assert snap.balance_sheet is not None
    snap.balance_sheet.total_assets = None
    assert missing_minimum_fundamentals(snap) == ["balance_sheet.total_assets"]

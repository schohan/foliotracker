"""Net Asset Intelligence T2 — adjusted net assets vs market."""

from __future__ import annotations

import pytest

from app.schemas.financials import FinancialMetrics, StatementSummary
from app.schemas.thesis import INSUFFICIENT_DATA, AssetVerdict
from app.services.thesis_net_assets import asset_breakdown_for


def _line(breakdown, name: str):
    for group in (breakdown.assets, breakdown.liabilities):
        for line in group:
            if line.name == name:
                return line
    raise KeyError(name)


def test_full_balance_sheet_adjusted_and_undervaluation() -> None:
    # market 48, adjusted 61 → difference (48−61)/61 ≈ −21.3% → undervaluation
    m = FinancialMetrics(
        ticker="X",
        market_cap=48.0,
        total_cash=10.0,
        total_debt=20.0,
        balance_sheet=StatementSummary(
            total_assets=100.0,
            total_liabilities=39.0,
            total_cash=10.0,
            total_debt=20.0,
        ),
    )
    b = asset_breakdown_for(m)
    assert b.adjusted_net_assets == pytest.approx(61.0)
    assert b.difference_pct == pytest.approx((48.0 - 61.0) / 61.0)
    assert b.verdict == AssetVerdict.POSSIBLE_UNDERVALUATION
    assert _line(b, "Cash").value == pytest.approx(10.0)
    assert _line(b, "Other Assets").value == pytest.approx(90.0)
    assert _line(b, "Total Debt").value == pytest.approx(20.0)
    assert _line(b, "Other Liabilities").value == pytest.approx(19.0)


def test_unavailable_line_items_stay_null() -> None:
    m = FinancialMetrics(
        ticker="X",
        market_cap=100.0,
        total_cash=5.0,
        balance_sheet=StatementSummary(total_assets=50.0, total_liabilities=10.0),
    )
    b = asset_breakdown_for(m)
    for name in ("Receivables", "Inventory", "Factories", "Land", "Investments", "Patents"):
        assert _line(b, name).value is None
    assert _line(b, "Lease").value is None


def test_fair_verdict_within_band() -> None:
    # market 100, adjusted 100 → 0% → Fair
    m = FinancialMetrics(
        ticker="X",
        market_cap=100.0,
        balance_sheet=StatementSummary(total_assets=150.0, total_liabilities=50.0),
    )
    b = asset_breakdown_for(m)
    assert b.verdict == AssetVerdict.FAIR
    assert b.difference_pct == pytest.approx(0.0)


def test_overvaluation_verdict() -> None:
    # market 200, adjusted 100 → +100% → overvaluation
    m = FinancialMetrics(
        ticker="X",
        market_cap=200.0,
        balance_sheet=StatementSummary(total_assets=150.0, total_liabilities=50.0),
    )
    b = asset_breakdown_for(m)
    assert b.verdict == AssetVerdict.POSSIBLE_OVERVALUATION


def test_missing_balance_sheet_nulls_adjusted() -> None:
    b = asset_breakdown_for(FinancialMetrics(ticker="X", market_cap=100.0))
    assert b.adjusted_net_assets is None
    assert b.difference_pct is None
    assert b.verdict is None
    assert INSUFFICIENT_DATA in b.detail

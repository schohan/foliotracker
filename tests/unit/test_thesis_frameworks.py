"""Framework Engine v1 — locked Graham + Financial Strength formulas."""

from __future__ import annotations

import pytest

from app.schemas.financials import FinancialMetrics, PeriodMetric, StatementSummary
from app.schemas.thesis import CheckStatus, FrameworkId
from app.services.thesis_frameworks import (
    financial_strength_scorecard,
    graham_scorecard,
    scorecards_for,
)


def _full_metrics(**overrides) -> FinancialMetrics:
    base = dict(
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
        earnings_history=[
            PeriodMetric(period=f"2025-Q{i}", value=1.0 + i) for i in range(1, 5)
        ],
        balance_sheet=StatementSummary(total_liabilities=50.0),
        cash_flow=StatementSummary(operating_cashflow=20.0),
    )
    base.update(overrides)
    return FinancialMetrics(**base)


def _check(card, name):
    return next(c for c in card.checks if c.name == name)


# ---------------------------------------------------------------- Graham


def test_graham_full_data_scores_high() -> None:
    card = graham_scorecard(_full_metrics())
    assert card.framework == FrameworkId.GRAHAM
    # Dividend History is always unknown in T1 → coverage 90, not 100.
    assert card.coverage == 90
    # All computable checks pass at 100 points.
    assert card.score == 100.0


def test_graham_margin_of_safety_math() -> None:
    # V = 5 × (8.5 + 2·10) = 142.5; P = 50; MoS = 92.5/142.5 ≈ 0.649
    card = graham_scorecard(_full_metrics())
    mos = _check(card, "Margin of Safety")
    assert mos.status == CheckStatus.PASS
    assert mos.value == pytest.approx(0.6491, abs=1e-3)
    assert mos.rating.startswith("Excellent")
    assert mos.points == 100.0


def test_graham_growth_clamped_at_15_percent() -> None:
    a = graham_scorecard(_full_metrics(earnings_growth=0.15))
    b = graham_scorecard(_full_metrics(earnings_growth=0.80))
    assert _check(a, "Margin of Safety").value == _check(b, "Margin of Safety").value


def test_graham_missing_growth_uses_no_growth_value() -> None:
    # g = 0 → V = 5 × 8.5 = 42.5; P = 50 → MoS negative → Poor / FAIL / 0 pts.
    card = graham_scorecard(_full_metrics(earnings_growth=None, trailing_pe=10.0))
    mos = _check(card, "Margin of Safety")
    assert mos.status == CheckStatus.FAIL
    assert mos.rating.startswith("Poor")
    assert mos.points == 0.0


def test_graham_mos_null_without_positive_eps_or_pe() -> None:
    for overrides in (
        {"eps_trailing": None},
        {"eps_trailing": -1.0},
        {"trailing_pe": None, "pe_ratio": None},
        {"trailing_pe": -5.0, "pe_ratio": None},
    ):
        card = graham_scorecard(_full_metrics(**overrides))
        mos = _check(card, "Margin of Safety")
        assert mos.status == CheckStatus.UNKNOWN
        assert mos.points is None
        assert "insufficient data" in mos.detail


def test_graham_net_net_pass_and_fail() -> None:
    passing = graham_scorecard(_full_metrics())
    assert _check(passing, "Net-Net (cash proxy)").status == CheckStatus.PASS
    failing = graham_scorecard(_full_metrics(market_cap=500.0))
    assert _check(failing, "Net-Net (cash proxy)").status == CheckStatus.FAIL


def test_graham_debt_percent_normalization() -> None:
    # Yahoo-style 150 (percent) → 1.5 → High / 0 points.
    card = graham_scorecard(_full_metrics(debt_to_equity=150.0))
    debt = _check(card, "Debt")
    assert debt.value == pytest.approx(1.5)
    assert debt.rating == "High"
    assert debt.points == 0.0


def test_graham_debt_moderate_band() -> None:
    card = graham_scorecard(_full_metrics(debt_to_equity=0.8))
    debt = _check(card, "Debt")
    assert debt.rating == "Moderate"
    assert debt.points == 50.0


def test_graham_earnings_stability_needs_four_periods() -> None:
    card = graham_scorecard(
        _full_metrics(
            earnings_history=[
                PeriodMetric(period="2025-Q1", value=1.0),
                PeriodMetric(period="2025-Q2", value=2.0),
            ]
        )
    )
    stability = _check(card, "Earnings Stability")
    assert stability.status == CheckStatus.UNKNOWN


def test_graham_earnings_stability_fails_on_loss_quarter() -> None:
    history = [
        PeriodMetric(period=f"2025-Q{i}", value=v)
        for i, v in enumerate((1.0, 2.0, -0.5, 3.0), start=1)
    ]
    card = graham_scorecard(_full_metrics(earnings_history=history))
    assert _check(card, "Earnings Stability").status == CheckStatus.FAIL


def test_graham_dividend_history_always_unknown_in_t1() -> None:
    card = graham_scorecard(_full_metrics())
    dividend = _check(card, "Dividend History")
    assert dividend.status == CheckStatus.UNKNOWN
    assert dividend.points is None


def test_graham_score_null_below_coverage() -> None:
    # Only current_ratio known → coverage 15 < 50 → null score.
    card = graham_scorecard(FinancialMetrics(ticker="X", current_ratio=2.5))
    assert card.coverage == 15
    assert card.score is None


def test_graham_composite_renormalizes_over_known_checks() -> None:
    # MoS 0 pts (w30) + Current Ratio 100 (w15) + Debt Moderate 50 (w15)
    # → (0·30 + 100·15 + 50·15) / 60 = 37.5
    metrics = FinancialMetrics(
        ticker="X",
        eps_trailing=5.0,
        trailing_pe=40.0,
        current_ratio=2.5,
        debt_to_equity=0.8,
    )
    card = graham_scorecard(metrics)
    assert card.coverage == 60
    assert card.score == pytest.approx(37.5)


def test_empty_metrics_all_unknown() -> None:
    card = graham_scorecard(FinancialMetrics(ticker="X"))
    assert card.score is None
    assert card.coverage == 0
    assert all(c.status == CheckStatus.UNKNOWN for c in card.checks)


# ---------------------------------------------------- Financial Strength


def test_financial_strength_full_data_perfect_score() -> None:
    card = financial_strength_scorecard(_full_metrics())
    assert card.framework == FrameworkId.FINANCIAL_STRENGTH
    assert card.coverage == 100
    assert card.score == 100.0


def test_financial_strength_leverage_bands() -> None:
    for dte, expected in ((0.4, 100.0), (0.8, 60.0), (1.5, 30.0), (3.0, 0.0)):
        card = financial_strength_scorecard(_full_metrics(debt_to_equity=dte))
        assert _check(card, "Leverage").points == expected


def test_financial_strength_roe_bands() -> None:
    for roe, expected, status in (
        (0.20, 100.0, CheckStatus.PASS),
        (0.12, 70.0, CheckStatus.PASS),
        (0.05, 30.0, CheckStatus.FAIL),
        (-0.10, 0.0, CheckStatus.FAIL),
    ):
        card = financial_strength_scorecard(_full_metrics(return_on_equity=roe))
        check = _check(card, "Return on equity")
        assert check.points == expected
        assert check.status == status


def test_financial_strength_profitability_falls_back_to_net_income() -> None:
    card = financial_strength_scorecard(
        _full_metrics(profit_margin=None, net_income_ttm=5.0)
    )
    assert _check(card, "Profitability").status == CheckStatus.PASS
    card = financial_strength_scorecard(
        _full_metrics(profit_margin=None, net_income_ttm=None)
    )
    assert _check(card, "Profitability").status == CheckStatus.UNKNOWN


def test_financial_strength_score_null_below_coverage() -> None:
    # Liquidity (20) + Leverage (20) = 40 < 50 → null.
    metrics = FinancialMetrics(ticker="X", current_ratio=2.0, debt_to_equity=0.4)
    card = financial_strength_scorecard(metrics)
    assert card.coverage == 40
    assert card.score is None


def test_financial_strength_net_cash_fail() -> None:
    card = financial_strength_scorecard(
        _full_metrics(total_cash=10.0, total_debt=80.0)
    )
    assert _check(card, "Net cash position").status == CheckStatus.FAIL


def test_scorecards_for_returns_both_frameworks() -> None:
    cards = scorecards_for(_full_metrics())
    assert [c.framework for c in cards] == [
        FrameworkId.GRAHAM,
        FrameworkId.FINANCIAL_STRENGTH,
    ]


def test_checks_cite_input_fields() -> None:
    card = graham_scorecard(_full_metrics())
    mos = _check(card, "Margin of Safety")
    assert "eps_trailing" in mos.inputs
    fs = financial_strength_scorecard(_full_metrics())
    ocf = _check(fs, "Operating cash flow")
    assert ocf.inputs == ["cash_flow.operating_cashflow"]

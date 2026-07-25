"""Unit tests for deterministic scoring service (Phase 2B)."""

from __future__ import annotations

import pytest

from app.schemas.financials import FinancialMetrics
from app.services.scoring import score_from_metrics


def _metrics(**kwargs) -> FinancialMetrics:
    base = {"ticker": "NVDA"}
    base.update(kwargs)
    return FinancialMetrics(**base)


def test_empty_metrics_returns_none() -> None:
    assert score_from_metrics(_metrics()) is None


def test_growth_score_higher_growth_higher_score() -> None:
    low = score_from_metrics(_metrics(revenue_growth=0.0))
    high = score_from_metrics(_metrics(revenue_growth=0.5))
    assert low is not None and high is not None
    assert low.growth_score is not None and high.growth_score is not None
    assert high.growth_score > low.growth_score


def test_growth_score_clamps_to_0_100() -> None:
    floor = score_from_metrics(_metrics(revenue_growth=-1.0))
    ceil = score_from_metrics(_metrics(revenue_growth=5.0))
    assert floor is not None and ceil is not None
    assert floor.growth_score == 0.0
    assert ceil.growth_score == 100.0


def test_value_score_lower_pe_higher_score() -> None:
    cheap = score_from_metrics(_metrics(pe_ratio=10.0))
    rich = score_from_metrics(_metrics(pe_ratio=40.0))
    assert cheap is not None and rich is not None
    assert cheap.value_score is not None and rich.value_score is not None
    assert cheap.value_score > rich.value_score


def test_value_score_non_positive_pe_is_null() -> None:
    zero = score_from_metrics(_metrics(pe_ratio=0.0))
    neg = score_from_metrics(_metrics(pe_ratio=-5.0))
    assert zero is not None and neg is not None
    assert zero.value_score is None
    assert neg.value_score is None


def test_value_score_uses_forward_pe_when_trailing_missing() -> None:
    card = score_from_metrics(_metrics(forward_pe=10.0))
    assert card is not None
    assert card.value_score is not None


def test_growth_score_falls_back_to_earnings_growth() -> None:
    card = score_from_metrics(_metrics(earnings_growth=0.5))
    assert card is not None
    assert card.growth_score is not None
    assert card.growth_score > 50.0


def test_value_score_clamps() -> None:
    floor = score_from_metrics(_metrics(pe_ratio=100.0))
    ceil = score_from_metrics(_metrics(pe_ratio=1.0))
    assert floor is not None and ceil is not None
    assert floor.value_score == 0.0
    assert ceil.value_score == 100.0


def test_profitability_prefers_operating_over_gross() -> None:
    both = score_from_metrics(
        _metrics(operating_margin=0.1, gross_margin=0.8)
    )
    op_only = score_from_metrics(_metrics(operating_margin=0.1))
    assert both is not None and op_only is not None
    assert both.profitability_score == op_only.profitability_score


def test_profitability_falls_back_to_gross() -> None:
    card = score_from_metrics(_metrics(gross_margin=0.5))
    assert card is not None
    assert card.profitability_score is not None
    assert card.profitability_score == pytest.approx(100.0)


def test_risk_score_higher_leverage_higher_risk() -> None:
    low = score_from_metrics(_metrics(debt_to_equity=0.2))
    high = score_from_metrics(_metrics(debt_to_equity=1.5))
    assert low is not None and high is not None
    assert low.risk_score is not None and high.risk_score is not None
    assert high.risk_score > low.risk_score


def test_risk_score_clamps() -> None:
    floor = score_from_metrics(_metrics(debt_to_equity=0.0))
    ceil = score_from_metrics(_metrics(debt_to_equity=10.0))
    assert floor is not None and ceil is not None
    assert floor.risk_score == 0.0
    assert ceil.risk_score == 100.0


def test_moat_from_gross_margin() -> None:
    low = score_from_metrics(_metrics(gross_margin=0.2))
    high = score_from_metrics(_metrics(gross_margin=0.8))
    assert low is not None and high is not None
    assert low.moat_score is not None and high.moat_score is not None
    assert high.moat_score > low.moat_score
    assert high.moat_score == 100.0


def test_execution_always_null() -> None:
    card = score_from_metrics(
        _metrics(
            revenue_growth=0.2,
            pe_ratio=20.0,
            operating_margin=0.3,
            gross_margin=0.5,
            debt_to_equity=0.5,
            free_cash_flow=1e9,
            market_cap=1e11,
        )
    )
    assert card is not None
    assert card.execution_score is None


def test_partial_scorecard_null_dims() -> None:
    card = score_from_metrics(_metrics(revenue_growth=0.1))
    assert card is not None
    assert card.ticker == "NVDA"
    assert card.growth_score is not None
    assert card.value_score is None
    assert card.profitability_score is None
    assert card.risk_score is None
    assert card.moat_score is None
    assert card.execution_score is None


def test_known_midpoints() -> None:
    """Documented clamp anchors: growth 0 → ~33.3; pe 27.5 → 50; dte 1 → 50."""
    card = score_from_metrics(
        _metrics(
            revenue_growth=0.0,
            pe_ratio=27.5,
            debt_to_equity=1.0,
            gross_margin=0.4,
            operating_margin=0.15,
        )
    )
    assert card is not None
    assert card.growth_score == pytest.approx(100.0 / 3.0)
    assert card.value_score == pytest.approx(50.0)
    assert card.risk_score == pytest.approx(50.0)
    # operating 0.15 → (0.15+0.2)/0.7*100 ≈ 50
    assert card.profitability_score == pytest.approx(50.0)
    assert card.moat_score == pytest.approx(50.0)

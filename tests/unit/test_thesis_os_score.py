"""Investment OS Score + portfolio health rollup (T5)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.schemas.financials import FinancialMetrics, PeriodMetric, StatementSummary
from app.schemas.thesis import (
    AssetBreakdown,
    AssetVerdict,
    InvestmentOSScore,
    MarginOfSafetyView,
    OSDimensionId,
    ThesisChange,
    ThesisMonitoring,
    ThesisTicker,
    ThesisVerdict,
)
from app.services.thesis_frameworks import scorecards_for
from app.services.thesis_os_score import (
    build_portfolio_rollup,
    compute_os_score,
    score_rating,
)
from app.services.thesis_valuations import margin_of_safety_for, valuation_set_for


def _rich_metrics(**overrides) -> FinancialMetrics:
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
        revenue_ttm=100.0,
        profit_margin=0.2,
        return_on_equity=0.18,
        balance_sheet=StatementSummary(total_liabilities=50.0, total_assets=300.0),
        cash_flow=StatementSummary(operating_cashflow=20.0, free_cash_flow=10.0),
        earnings_history=[
            PeriodMetric(period="2023Q1", value=1.0),
            PeriodMetric(period="2023Q2", value=1.1),
            PeriodMetric(period="2023Q3", value=1.2),
            PeriodMetric(period="2023Q4", value=1.3),
        ],
    )
    base.update(overrides)
    return FinancialMetrics(**base)


def _monitoring(verdict: ThesisVerdict) -> ThesisMonitoring:
    return ThesisMonitoring(
        original_thesis="seed",
        current=ThesisChange(
            verdict=verdict,
            as_of=datetime(2026, 8, 7, tzinfo=timezone.utc),
            evidence=["baseline — no prior quarter"],
        ),
    )


def test_score_rating_bands() -> None:
    assert score_rating(92) == "Excellent"
    assert score_rating(70) == "Good"
    assert score_rating(50) == "Fair"
    assert score_rating(30) == "Weak"
    assert score_rating(10) == "Poor"
    assert score_rating(None) == ""


def test_os_score_rich_ticker_has_composite() -> None:
    metrics = _rich_metrics()
    frameworks = scorecards_for(metrics)
    mos = margin_of_safety_for(metrics)
    valuation = valuation_set_for(metrics)
    result = compute_os_score(
        frameworks=frameworks,
        mos_view=mos,
        valuation=valuation,
        monitoring=_monitoring(ThesisVerdict.NO_CHANGE),
    )
    assert result.score is not None
    assert result.coverage >= 50
    assert result.rating
    assert len(result.dimensions) == 8
    ids = {d.id for d in result.dimensions}
    assert ids == set(OSDimensionId)


def test_valuation_dimension_from_mos() -> None:
    frameworks = scorecards_for(_rich_metrics())
    mos = MarginOfSafetyView(margin_of_safety=0.25)
    result = compute_os_score(frameworks=frameworks, mos_view=mos)
    val = next(d for d in result.dimensions if d.id == OSDimensionId.VALUATION)
    assert val.points == 50.0  # 0.25 / 0.50 * 100


def test_framework_consensus_perfect_agreement() -> None:
    # Force both frameworks to similar scores via rich metrics.
    frameworks = scorecards_for(_rich_metrics())
    result = compute_os_score(
        frameworks=frameworks,
        mos_view=MarginOfSafetyView(margin_of_safety=0.2),
        monitoring=_monitoring(ThesisVerdict.STRENGTHENED),
    )
    consensus = next(
        d for d in result.dimensions if d.id == OSDimensionId.FRAMEWORK_CONSENSUS
    )
    assert consensus.points is not None
    assert consensus.points >= 80


def test_thesis_stability_broken_is_zero() -> None:
    frameworks = scorecards_for(_rich_metrics())
    result = compute_os_score(
        frameworks=frameworks,
        mos_view=MarginOfSafetyView(margin_of_safety=0.2),
        monitoring=_monitoring(ThesisVerdict.BROKEN),
    )
    stab = next(
        d for d in result.dimensions if d.id == OSDimensionId.THESIS_STABILITY
    )
    assert stab.points == 0.0


def test_low_coverage_null_score() -> None:
    # Bare metrics → many null dimensions / low coverage.
    frameworks = scorecards_for(FinancialMetrics(ticker="X"))
    result = compute_os_score(frameworks=frameworks)
    assert result.score is None
    assert result.coverage < 50


def test_portfolio_rollup_counts() -> None:
    metrics = _rich_metrics()
    frameworks = scorecards_for(metrics)
    mos = margin_of_safety_for(metrics)
    valuation = valuation_set_for(metrics)
    os_score = compute_os_score(
        frameworks=frameworks,
        mos_view=mos,
        valuation=valuation,
        monitoring=_monitoring(ThesisVerdict.NO_CHANGE),
    )

    strong = ThesisTicker(
        ticker="A",
        list_kind="held",
        frameworks=frameworks,
        margin_of_safety=mos,
        assets=AssetBreakdown(verdict=AssetVerdict.POSSIBLE_UNDERVALUATION),
        monitoring=_monitoring(ThesisVerdict.NO_CHANGE),
        os_score=os_score,
    )
    broken = ThesisTicker(
        ticker="B",
        list_kind="watched",
        frameworks=frameworks,
        margin_of_safety=MarginOfSafetyView(margin_of_safety=-0.2),
        assets=AssetBreakdown(verdict=AssetVerdict.POSSIBLE_OVERVALUATION),
        monitoring=_monitoring(ThesisVerdict.BROKEN),
        os_score=InvestmentOSScore(score=40.0, rating="Weak", coverage=80),
    )
    rollup = build_portfolio_rollup([strong, broken])
    assert rollup.tickers_scored == 2
    assert rollup.health_score is not None
    assert rollup.thesis_broken == 1
    assert rollup.overvalued >= 1
    assert rollup.significantly_undervalued >= 1

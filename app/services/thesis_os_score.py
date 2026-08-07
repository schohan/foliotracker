"""Investment OS Score + portfolio health rollup (T5).

Implements architecture.md "Investment OS Score specs" (2026-08-07).
Pure Python over T1–T4 outputs; missing inputs → null dimensions, never invented.
"""

from __future__ import annotations

from app.schemas.thesis import (
    OS_DIMENSION_LABELS,
    OS_DIMENSION_WEIGHTS,
    AssetBreakdown,
    AssetVerdict,
    FrameworkId,
    FrameworkScorecard,
    InvestmentOSScore,
    MarginOfSafetyView,
    OSDimension,
    OSDimensionId,
    PortfolioHealthRollup,
    ThesisMonitoring,
    ThesisTicker,
    ThesisVerdict,
    ValuationSet,
)

# Shared with frameworks: score null below this weight coverage.
MIN_COVERAGE = 50

# Valuation MoS → points ceiling (same as Graham MoS check).
_MOS_POINTS_CEIL = 0.50

# FCF yield → capital allocation points (0% → 0, ≥8% → 100).
_FCF_YIELD_CEIL = 0.08

# Portfolio rollup thresholds
_BS_STRONG = 70.0
_BS_WEAK = 40.0
_HIGH_CONVICTION = 75.0
_VALUE_TRAP_FS = 60.0
_UNDERVALUED_MOS = 0.30


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def score_rating(score: float | None) -> str:
    if score is None:
        return ""
    if score >= 85:
        return "Excellent"
    if score >= 70:
        return "Good"
    if score >= 50:
        return "Fair"
    if score >= 30:
        return "Weak"
    return "Poor"


def _check_points(card: FrameworkScorecard | None, name: str) -> float | None:
    if card is None:
        return None
    for check in card.checks:
        if check.name == name:
            return check.points
    return None


def _card_for(
    frameworks: list[FrameworkScorecard], framework: FrameworkId
) -> FrameworkScorecard | None:
    for card in frameworks:
        if card.framework == framework:
            return card
    return None


def _mean_known(values: list[float | None]) -> float | None:
    known = [v for v in values if v is not None]
    if not known:
        return None
    return sum(known) / len(known)


def _dim(
    dim_id: OSDimensionId, points: float | None, detail: str = ""
) -> OSDimension:
    return OSDimension(
        id=dim_id,
        label=OS_DIMENSION_LABELS[dim_id],
        weight=OS_DIMENSION_WEIGHTS[dim_id],
        points=None if points is None else round(points, 2),
        detail=detail,
    )


def _business_quality(fs: FrameworkScorecard | None) -> OSDimension:
    profit = _check_points(fs, "Profitability")
    roe = _check_points(fs, "Return on equity")
    pts = _mean_known([profit, roe])
    bits = []
    if profit is not None:
        bits.append(f"profitability={profit:.0f}")
    if roe is not None:
        bits.append(f"roe={roe:.0f}")
    return _dim(
        OSDimensionId.BUSINESS_QUALITY,
        pts,
        detail="; ".join(bits) if bits else "insufficient data: profitability, roe",
    )


def _financial_strength(fs: FrameworkScorecard | None) -> OSDimension:
    score = fs.score if fs is not None else None
    return _dim(
        OSDimensionId.FINANCIAL_STRENGTH,
        score,
        detail=f"fs_score={score:.0f}" if score is not None else "insufficient data: fs_score",
    )


def _valuation(mos_view: MarginOfSafetyView | None) -> OSDimension:
    mos = mos_view.margin_of_safety if mos_view is not None else None
    if mos is None:
        return _dim(
            OSDimensionId.VALUATION,
            None,
            detail="insufficient data: margin_of_safety",
        )
    pts = _clamp(mos / _MOS_POINTS_CEIL, 0.0, 1.0) * 100.0
    return _dim(
        OSDimensionId.VALUATION,
        pts,
        detail=f"mos={mos * 100:.0f}% → points via clamp(mos/0.50)",
    )


def _balance_sheet(fs: FrameworkScorecard | None) -> OSDimension:
    liq = _check_points(fs, "Liquidity")
    lev = _check_points(fs, "Leverage")
    net = _check_points(fs, "Net cash position")
    pts = _mean_known([liq, lev, net])
    bits = []
    if liq is not None:
        bits.append(f"liquidity={liq:.0f}")
    if lev is not None:
        bits.append(f"leverage={lev:.0f}")
    if net is not None:
        bits.append(f"net_cash={net:.0f}")
    return _dim(
        OSDimensionId.BALANCE_SHEET,
        pts,
        detail="; ".join(bits)
        if bits
        else "insufficient data: liquidity, leverage, net_cash",
    )


def _earnings_quality(
    graham: FrameworkScorecard | None, fs: FrameworkScorecard | None
) -> OSDimension:
    stab = _check_points(graham, "Earnings Stability")
    ocf = _check_points(fs, "Operating cash flow")
    pts = _mean_known([stab, ocf])
    bits = []
    if stab is not None:
        bits.append(f"earnings_stability={stab:.0f}")
    if ocf is not None:
        bits.append(f"ocf={ocf:.0f}")
    return _dim(
        OSDimensionId.EARNINGS_QUALITY,
        pts,
        detail="; ".join(bits)
        if bits
        else "insufficient data: earnings_stability, ocf",
    )


def _capital_allocation(
    fs: FrameworkScorecard | None, valuation: ValuationSet | None
) -> OSDimension:
    fcf_yield: float | None = None
    if valuation is not None:
        for method in valuation.buffett:
            if method.id == "fcf_yield" and method.value is not None:
                fcf_yield = method.value
                break
    if fcf_yield is not None:
        pts = _clamp(fcf_yield / _FCF_YIELD_CEIL, 0.0, 1.0) * 100.0
        return _dim(
            OSDimensionId.CAPITAL_ALLOCATION,
            pts,
            detail=f"fcf_yield={fcf_yield * 100:.1f}%",
        )
    fcf_check = _check_points(fs, "Free cash flow")
    if fcf_check is not None:
        return _dim(
            OSDimensionId.CAPITAL_ALLOCATION,
            fcf_check,
            detail=f"fcf_check={fcf_check:.0f} (yield unavailable)",
        )
    return _dim(
        OSDimensionId.CAPITAL_ALLOCATION,
        None,
        detail="insufficient data: fcf_yield, free_cash_flow",
    )


def _framework_consensus(
    graham: FrameworkScorecard | None, fs: FrameworkScorecard | None
) -> OSDimension:
    g = graham.score if graham is not None else None
    f = fs.score if fs is not None else None
    if g is None or f is None:
        return _dim(
            OSDimensionId.FRAMEWORK_CONSENSUS,
            None,
            detail="insufficient data: both graham and fs scores required",
        )
    pts = 100.0 - min(100.0, abs(g - f) * 2.0)
    return _dim(
        OSDimensionId.FRAMEWORK_CONSENSUS,
        pts,
        detail=f"|graham−fs|={abs(g - f):.0f}",
    )


def _thesis_stability(monitoring: ThesisMonitoring | None) -> OSDimension:
    if monitoring is None or monitoring.current is None:
        return _dim(
            OSDimensionId.THESIS_STABILITY,
            None,
            detail="insufficient data: thesis verdict",
        )
    verdict = monitoring.current.verdict
    mapping = {
        ThesisVerdict.STRENGTHENED: 100.0,
        ThesisVerdict.NO_CHANGE: 75.0,
        ThesisVerdict.SLIGHTLY_WEAKER: 35.0,
        ThesisVerdict.BROKEN: 0.0,
    }
    pts = mapping[verdict]
    return _dim(
        OSDimensionId.THESIS_STABILITY,
        pts,
        detail=f"verdict={verdict.value}",
    )


def compute_os_score(
    *,
    frameworks: list[FrameworkScorecard],
    mos_view: MarginOfSafetyView | None = None,
    valuation: ValuationSet | None = None,
    monitoring: ThesisMonitoring | None = None,
) -> InvestmentOSScore:
    """Build Investment OS Score from T1–T4 signals."""
    graham = _card_for(frameworks, FrameworkId.GRAHAM)
    fs = _card_for(frameworks, FrameworkId.FINANCIAL_STRENGTH)

    dimensions = [
        _business_quality(fs),
        _financial_strength(fs),
        _valuation(mos_view),
        _balance_sheet(fs),
        _earnings_quality(graham, fs),
        _capital_allocation(fs, valuation),
        _framework_consensus(graham, fs),
        _thesis_stability(monitoring),
    ]

    known_weight = sum(d.weight for d in dimensions if d.points is not None)
    if known_weight < MIN_COVERAGE:
        return InvestmentOSScore(
            score=None,
            rating="",
            coverage=known_weight,
            dimensions=dimensions,
        )

    weighted = sum(
        d.points * d.weight for d in dimensions if d.points is not None
    )
    score = round(weighted / known_weight, 2)
    return InvestmentOSScore(
        score=score,
        rating=score_rating(score),
        coverage=known_weight,
        dimensions=dimensions,
    )


def _balance_sheet_points(os_score: InvestmentOSScore | None) -> float | None:
    if os_score is None:
        return None
    for d in os_score.dimensions:
        if d.id == OSDimensionId.BALANCE_SHEET:
            return d.points
    return None


def _fs_score(row: ThesisTicker) -> float | None:
    card = _card_for(row.frameworks, FrameworkId.FINANCIAL_STRENGTH)
    return card.score if card is not None else None


def build_portfolio_rollup(tickers: list[ThesisTicker]) -> PortfolioHealthRollup:
    """Aggregate portfolio health counts (PRD §5.4.8)."""
    scores = [
        t.os_score.score
        for t in tickers
        if t.os_score is not None and t.os_score.score is not None
    ]
    health = round(sum(scores) / len(scores), 2) if scores else None

    strong_bs = 0
    weak_bs = 0
    traps = 0
    undervalued = 0
    overvalued = 0
    conviction = 0
    broken = 0

    for row in tickers:
        bs = _balance_sheet_points(row.os_score)
        fs = _fs_score(row)
        mos = (
            row.margin_of_safety.margin_of_safety
            if row.margin_of_safety is not None
            else None
        )
        assets: AssetBreakdown | None = row.assets

        if (bs is not None and bs >= _BS_STRONG) or (
            fs is not None and fs >= _BS_STRONG
        ):
            strong_bs += 1
        if (bs is not None and bs < _BS_WEAK) or (
            fs is not None and fs < _BS_WEAK
        ):
            weak_bs += 1

        if mos is not None and mos < 0 and fs is not None and fs >= _VALUE_TRAP_FS:
            traps += 1

        undervalued_hit = (mos is not None and mos >= _UNDERVALUED_MOS) or (
            assets is not None
            and assets.verdict == AssetVerdict.POSSIBLE_UNDERVALUATION
        )
        if undervalued_hit:
            undervalued += 1

        overvalued_hit = (mos is not None and mos < 0) or (
            assets is not None
            and assets.verdict == AssetVerdict.POSSIBLE_OVERVALUATION
        )
        if overvalued_hit:
            overvalued += 1

        if row.os_score is not None and row.os_score.score is not None:
            if row.os_score.score >= _HIGH_CONVICTION:
                conviction += 1

        if (
            row.monitoring is not None
            and row.monitoring.current is not None
            and row.monitoring.current.verdict == ThesisVerdict.BROKEN
        ):
            broken += 1

    return PortfolioHealthRollup(
        health_score=health,
        health_rating=score_rating(health),
        tickers_scored=len(scores),
        strong_balance_sheets=strong_bs,
        weak_balance_sheets=weak_bs,
        potential_value_traps=traps,
        significantly_undervalued=undervalued,
        overvalued=overvalued,
        high_conviction=conviction,
        thesis_broken=broken,
    )

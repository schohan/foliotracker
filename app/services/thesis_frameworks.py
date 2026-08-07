"""Framework Engine v1 — deterministic Graham + Financial Strength scorecards.

Implements the locked spec tables in architecture.md "Framework formula
specs" (2026-08-07). Pure Python over the merged FundamentalsSnapshot;
missing inputs → check ``unknown`` ("insufficient data"), never invented.
"""

from __future__ import annotations

from app.schemas.financials import FinancialMetrics
from app.schemas.thesis import (
    FRAMEWORK_LABELS,
    INSUFFICIENT_DATA,
    CheckStatus,
    FrameworkCheck,
    FrameworkId,
    FrameworkScorecard,
)

# Composite: score null when non-null check weight coverage below this.
MIN_COVERAGE = 50

# Graham locked constants
_GRAHAM_GROWTH_CAP = 0.15
_MOS_POINTS_CEIL = 0.50
_GRAHAM_CURRENT_RATIO_MIN = 2.0
_EARNINGS_STABILITY_MIN_PERIODS = 4

# Financial Strength locked constants
_FS_CURRENT_RATIO_MIN = 1.5

# Yahoo reports debt_to_equity in percent; values above this are percent.
_DTE_PERCENT_THRESHOLD = 10.0


def _norm_dte(debt_to_equity: float) -> float:
    """Normalize D/E: values > 10 are treated as percent (Yahoo convention)."""
    if debt_to_equity > _DTE_PERCENT_THRESHOLD:
        return debt_to_equity / 100.0
    return debt_to_equity


def _unknown(
    name: str, weight: int, inputs: list[str], missing: list[str]
) -> FrameworkCheck:
    return FrameworkCheck(
        name=name,
        status=CheckStatus.UNKNOWN,
        weight=weight,
        inputs=inputs,
        detail=f"{INSUFFICIENT_DATA}: {', '.join(missing)}",
    )


def _binary(
    *,
    name: str,
    weight: int,
    inputs: list[str],
    passed: bool,
    value: float | None = None,
    detail: str = "",
) -> FrameworkCheck:
    return FrameworkCheck(
        name=name,
        status=CheckStatus.PASS if passed else CheckStatus.FAIL,
        value=value,
        points=100.0 if passed else 0.0,
        weight=weight,
        inputs=inputs,
        detail=detail,
    )


def _margin_of_safety_check(m: FinancialMetrics) -> FrameworkCheck:
    name = "Margin of Safety"
    weight = 30
    inputs = ["eps_trailing", "trailing_pe", "pe_ratio", "earnings_growth"]
    eps = m.eps_trailing
    pe = None
    for candidate in (m.trailing_pe, m.pe_ratio):
        if candidate is not None and candidate > 0:
            pe = candidate
            break
    missing: list[str] = []
    if eps is None or eps <= 0:
        missing.append("eps_trailing")
    if pe is None:
        missing.append("positive trailing P/E")
    if missing:
        return _unknown(name, weight, inputs, missing)

    growth = m.earnings_growth if m.earnings_growth is not None else 0.0
    g = max(0.0, min(_GRAHAM_GROWTH_CAP, growth))
    intrinsic = eps * (8.5 + 2.0 * g * 100.0)
    price = pe * eps
    mos = (intrinsic - price) / intrinsic
    points = max(0.0, min(1.0, mos / _MOS_POINTS_CEIL)) * 100.0
    if mos >= 0.30:
        label = "Excellent"
    elif mos >= 0.15:
        label = "Good"
    elif mos >= 0.0:
        label = "Fair"
    else:
        label = "Poor"
    pct = mos * 100.0
    return FrameworkCheck(
        name=name,
        status=CheckStatus.PASS if mos >= 0.0 else CheckStatus.FAIL,
        value=round(mos, 4),
        rating=f"{label} — {pct:.0f}%",
        points=points,
        weight=weight,
        inputs=inputs,
        detail=(
            f"intrinsic {intrinsic:.2f} vs implied price {price:.2f}"
            f" (g={g:.0%})"
        ),
    )


def _net_net_check(m: FinancialMetrics) -> FrameworkCheck:
    name = "Net-Net (cash proxy)"
    weight = 10
    inputs = ["total_cash", "balance_sheet.total_liabilities", "market_cap"]
    liabilities = (
        m.balance_sheet.total_liabilities if m.balance_sheet is not None else None
    )
    missing = [
        label
        for label, val in (
            ("total_cash", m.total_cash),
            ("balance_sheet.total_liabilities", liabilities),
            ("market_cap", m.market_cap),
        )
        if val is None
    ]
    if missing:
        return _unknown(name, weight, inputs, missing)
    proxy = m.total_cash - liabilities
    passed = proxy >= m.market_cap
    return _binary(
        name=name,
        weight=weight,
        inputs=inputs,
        passed=passed,
        value=proxy,
        detail="cash-based NCAV proxy vs market cap",
    )


def _current_ratio_check(
    m: FinancialMetrics, *, name: str, weight: int, minimum: float
) -> FrameworkCheck:
    inputs = ["current_ratio"]
    if m.current_ratio is None:
        return _unknown(name, weight, inputs, ["current_ratio"])
    return _binary(
        name=name,
        weight=weight,
        inputs=inputs,
        passed=m.current_ratio >= minimum,
        value=m.current_ratio,
        detail=f"threshold ≥ {minimum:g}",
    )


def _graham_debt_check(m: FinancialMetrics) -> FrameworkCheck:
    name = "Debt"
    weight = 15
    inputs = ["debt_to_equity"]
    if m.debt_to_equity is None:
        return _unknown(name, weight, inputs, ["debt_to_equity"])
    dte = _norm_dte(m.debt_to_equity)
    if dte <= 0.5:
        rating, points, status = "Low", 100.0, CheckStatus.PASS
    elif dte <= 1.0:
        rating, points, status = "Moderate", 50.0, CheckStatus.FAIL
    else:
        rating, points, status = "High", 0.0, CheckStatus.FAIL
    return FrameworkCheck(
        name=name,
        status=status,
        value=round(dte, 3),
        rating=rating,
        points=points,
        weight=weight,
        inputs=inputs,
        detail="debt-to-equity (percent-normalized)",
    )


def _earnings_stability_check(m: FinancialMetrics) -> FrameworkCheck:
    name = "Earnings Stability"
    weight = 20
    inputs = ["earnings_history"]
    known = [p.value for p in m.earnings_history if p.value is not None]
    if len(known) < _EARNINGS_STABILITY_MIN_PERIODS:
        return _unknown(
            name,
            weight,
            inputs,
            [f"earnings_history (< {_EARNINGS_STABILITY_MIN_PERIODS} periods)"],
        )
    passed = all(v > 0 for v in known)
    return _binary(
        name=name,
        weight=weight,
        inputs=inputs,
        passed=passed,
        detail=f"{len(known)} known periods, all positive required",
    )


def _dividend_history_check() -> FrameworkCheck:
    # No dividend fields in current sources — honest T1 gap (locked spec).
    return _unknown("Dividend History", 10, [], ["dividend data (no source)"])


def _leverage_check(m: FinancialMetrics) -> FrameworkCheck:
    name = "Leverage"
    weight = 20
    inputs = ["debt_to_equity"]
    if m.debt_to_equity is None:
        return _unknown(name, weight, inputs, ["debt_to_equity"])
    dte = _norm_dte(m.debt_to_equity)
    if dte <= 0.5:
        points = 100.0
    elif dte <= 1.0:
        points = 60.0
    elif dte <= 2.0:
        points = 30.0
    else:
        points = 0.0
    return FrameworkCheck(
        name=name,
        status=CheckStatus.PASS if dte <= 1.0 else CheckStatus.FAIL,
        value=round(dte, 3),
        points=points,
        weight=weight,
        inputs=inputs,
        detail="debt-to-equity (percent-normalized)",
    )


def _net_cash_check(m: FinancialMetrics) -> FrameworkCheck:
    name = "Net cash position"
    weight = 15
    inputs = ["total_cash", "total_debt"]
    missing = [
        label
        for label, val in (("total_cash", m.total_cash), ("total_debt", m.total_debt))
        if val is None
    ]
    if missing:
        return _unknown(name, weight, inputs, missing)
    passed = m.total_cash >= m.total_debt
    return _binary(
        name=name,
        weight=weight,
        inputs=inputs,
        passed=passed,
        value=m.total_cash - m.total_debt,
        detail="cash minus total debt",
    )


def _fcf_check(m: FinancialMetrics) -> FrameworkCheck:
    name = "Free cash flow"
    weight = 15
    inputs = ["free_cash_flow"]
    if m.free_cash_flow is None:
        return _unknown(name, weight, inputs, ["free_cash_flow"])
    return _binary(
        name=name,
        weight=weight,
        inputs=inputs,
        passed=m.free_cash_flow > 0,
        value=m.free_cash_flow,
        detail="positive required",
    )


def _ocf_check(m: FinancialMetrics) -> FrameworkCheck:
    name = "Operating cash flow"
    weight = 10
    inputs = ["cash_flow.operating_cashflow"]
    ocf = m.cash_flow.operating_cashflow if m.cash_flow is not None else None
    if ocf is None:
        return _unknown(name, weight, inputs, ["cash_flow.operating_cashflow"])
    return _binary(
        name=name,
        weight=weight,
        inputs=inputs,
        passed=ocf > 0,
        value=ocf,
        detail="positive required",
    )


def _profitability_check(m: FinancialMetrics) -> FrameworkCheck:
    name = "Profitability"
    weight = 10
    inputs = ["profit_margin", "net_income_ttm"]
    if m.profit_margin is not None:
        return _binary(
            name=name,
            weight=weight,
            inputs=inputs,
            passed=m.profit_margin > 0,
            value=m.profit_margin,
            detail="profit margin positive required",
        )
    if m.net_income_ttm is not None:
        return _binary(
            name=name,
            weight=weight,
            inputs=inputs,
            passed=m.net_income_ttm > 0,
            value=m.net_income_ttm,
            detail="TTM net income positive required (margin unavailable)",
        )
    return _unknown(name, weight, inputs, ["profit_margin", "net_income_ttm"])


def _roe_check(m: FinancialMetrics) -> FrameworkCheck:
    name = "Return on equity"
    weight = 10
    inputs = ["return_on_equity"]
    roe = m.return_on_equity
    if roe is None:
        return _unknown(name, weight, inputs, ["return_on_equity"])
    if roe >= 0.15:
        points = 100.0
    elif roe >= 0.10:
        points = 70.0
    elif roe >= 0.0:
        points = 30.0
    else:
        points = 0.0
    return FrameworkCheck(
        name=name,
        status=CheckStatus.PASS if roe >= 0.10 else CheckStatus.FAIL,
        value=round(roe, 4),
        points=points,
        weight=weight,
        inputs=inputs,
        detail="thresholds 15% / 10% / 0%",
    )


def _composite(
    framework: FrameworkId, checks: list[FrameworkCheck]
) -> FrameworkScorecard:
    """Weighted mean over non-null checks, renormalized; null below coverage."""
    known = [c for c in checks if c.points is not None]
    coverage = sum(c.weight for c in known)
    score: float | None = None
    if coverage >= MIN_COVERAGE and coverage > 0:
        score = sum(c.points * c.weight for c in known) / coverage
        score = max(0.0, min(100.0, round(score, 1)))
    return FrameworkScorecard(
        framework=framework,
        label=FRAMEWORK_LABELS[framework],
        score=score,
        checks=checks,
        coverage=coverage,
    )


def graham_scorecard(metrics: FinancialMetrics) -> FrameworkScorecard:
    """Graham Deep Value per the locked spec table."""
    checks = [
        _margin_of_safety_check(metrics),
        _net_net_check(metrics),
        _current_ratio_check(
            metrics,
            name="Current Ratio",
            weight=15,
            minimum=_GRAHAM_CURRENT_RATIO_MIN,
        ),
        _graham_debt_check(metrics),
        _earnings_stability_check(metrics),
        _dividend_history_check(),
    ]
    return _composite(FrameworkId.GRAHAM, checks)


def financial_strength_scorecard(metrics: FinancialMetrics) -> FrameworkScorecard:
    """Financial Strength per the locked spec table."""
    checks = [
        _current_ratio_check(
            metrics,
            name="Liquidity",
            weight=20,
            minimum=_FS_CURRENT_RATIO_MIN,
        ),
        _leverage_check(metrics),
        _net_cash_check(metrics),
        _fcf_check(metrics),
        _ocf_check(metrics),
        _profitability_check(metrics),
        _roe_check(metrics),
    ]
    return _composite(FrameworkId.FINANCIAL_STRENGTH, checks)


def scorecards_for(metrics: FinancialMetrics) -> list[FrameworkScorecard]:
    """All T1 framework scorecards for one merged snapshot."""
    return [graham_scorecard(metrics), financial_strength_scorecard(metrics)]

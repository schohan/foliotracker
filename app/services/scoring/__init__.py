"""Scoring layer (growth, value, moat, risk, etc.).

Deterministic FinancialMetrics → Scorecard. Never let LLMs perform arithmetic.
"""

from __future__ import annotations

from app.schemas.financials import FinancialMetrics
from app.schemas.report import Scorecard

# Clamp anchors (documented in architecture). Inputs outside range clamp to 0–100.
# growth: revenue_growth fraction — -0.50 → 0, +1.00 → 100
_GROWTH_FLOOR = -0.50
_GROWTH_CEIL = 1.00
# value: pe_ratio — 5 → 100, 50 → 0 (non-positive → null)
_PE_BEST = 5.0
_PE_WORST = 50.0
# profitability / margin: fraction — -0.20 → 0, 0.50 → 100
_MARGIN_FLOOR = -0.20
_MARGIN_CEIL = 0.50
# risk: debt_to_equity — 0 → 0, 2.0 → 100
_DTE_CEIL = 2.0
# moat (provisional): gross_margin — 0 → 0, 0.80 → 100
_MOAT_CEIL = 0.80

_SCORABLE_FIELDS = (
    "revenue_growth",
    "pe_ratio",
    "gross_margin",
    "operating_margin",
    "debt_to_equity",
)


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _linear_up(value: float, floor: float, ceil: float) -> float:
    """Map [floor, ceil] → [0, 100]; higher input → higher score."""
    span = ceil - floor
    return _clamp((value - floor) / span * 100.0)


def _linear_down(value: float, best: float, worst: float) -> float:
    """Map [best, worst] → [100, 0]; lower input → higher score."""
    span = worst - best
    return _clamp((worst - value) / span * 100.0)


def _has_scorable_input(metrics: FinancialMetrics) -> bool:
    return any(getattr(metrics, field) is not None for field in _SCORABLE_FIELDS)


def score_from_metrics(metrics: FinancialMetrics) -> Scorecard | None:
    """Build a Scorecard from Yahoo metrics. Partial nulls ok; empty → None."""
    if not _has_scorable_input(metrics):
        return None

    growth = None
    if metrics.revenue_growth is not None:
        growth = _linear_up(metrics.revenue_growth, _GROWTH_FLOOR, _GROWTH_CEIL)

    value = None
    if metrics.pe_ratio is not None and metrics.pe_ratio > 0:
        value = _linear_down(metrics.pe_ratio, _PE_BEST, _PE_WORST)

    profitability = None
    margin = (
        metrics.operating_margin
        if metrics.operating_margin is not None
        else metrics.gross_margin
    )
    if margin is not None:
        profitability = _linear_up(margin, _MARGIN_FLOOR, _MARGIN_CEIL)

    risk = None
    if metrics.debt_to_equity is not None:
        risk = _clamp(metrics.debt_to_equity / _DTE_CEIL * 100.0)

    moat = None
    if metrics.gross_margin is not None:
        moat = _clamp(metrics.gross_margin / _MOAT_CEIL * 100.0)

    return Scorecard(
        ticker=metrics.ticker,
        growth_score=growth,
        value_score=value,
        profitability_score=profitability,
        moat_score=moat,
        risk_score=risk,
        execution_score=None,
    )

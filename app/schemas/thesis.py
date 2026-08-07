"""Thesis page contracts — T1 frameworks + T2 valuation / net assets / MoS.

Formulas and thresholds are locked in architecture.md "Framework formula
specs" (T1) and "Valuation / net-asset formula specs" (T2) before any
agent consumes these values (2B invariant).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.phase0 import PHASE0_DISCLAIMER

INSUFFICIENT_DATA = "insufficient data"


class FrameworkId(str, Enum):
    GRAHAM = "graham"
    FINANCIAL_STRENGTH = "financial_strength"


FRAMEWORK_LABELS: dict[FrameworkId, str] = {
    FrameworkId.GRAHAM: "Graham Deep Value",
    FrameworkId.FINANCIAL_STRENGTH: "Financial Strength",
}


class CheckStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"


class ThesisGenerationStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"


class ValuationSchool(str, Enum):
    GRAHAM = "graham"
    BUFFETT = "buffett"
    MODERN = "modern"


class ValuationUnit(str, Enum):
    CURRENCY = "currency"
    RATIO = "ratio"
    MULTIPLE = "multiple"
    PERCENT = "percent"


class AssetVerdict(str, Enum):
    POSSIBLE_UNDERVALUATION = "possible_undervaluation"
    FAIR = "fair"
    POSSIBLE_OVERVALUATION = "possible_overvaluation"


class FrameworkCheck(BaseModel):
    """One named framework check (deterministic; never invents inputs)."""

    name: str
    status: CheckStatus = CheckStatus.UNKNOWN
    # Raw input value shown to the user (e.g. current ratio 2.8), when numeric.
    value: float | None = None
    # Graded label (e.g. "Excellent — 34%", "Low"); empty when binary.
    rating: str = ""
    # 0–100 contribution to the framework composite; null when unknown.
    points: float | None = Field(default=None, ge=0, le=100)
    weight: int = Field(ge=0, le=100)
    # Merged-fundamentals field paths this check consumed (citation).
    inputs: list[str] = Field(default_factory=list)
    # Human line: formula result or "insufficient data: <fields>".
    detail: str = ""


class FrameworkScorecard(BaseModel):
    """Per-framework score for one ticker (0–100 or null) + named checks."""

    framework: FrameworkId
    label: str
    score: float | None = Field(default=None, ge=0, le=100)
    checks: list[FrameworkCheck] = Field(default_factory=list)
    # Sum of weights of non-null checks (coverage; score null below 50).
    coverage: int = Field(default=0, ge=0, le=100)


class ValuationMethod(BaseModel):
    """One named valuation method (deterministic; null when unsupported)."""

    id: str
    label: str
    school: ValuationSchool
    value: float | None = None
    unit: ValuationUnit = ValuationUnit.CURRENCY
    inputs: list[str] = Field(default_factory=list)
    detail: str = ""


class ValuationLadder(BaseModel):
    """Six-value ladder (firm $); Replacement always null until method locked."""

    market: float | None = None
    intrinsic: float | None = None
    liquidation: float | None = None
    replacement: float | None = None
    enterprise: float | None = None
    expected_fair: float | None = None


class ValuationSet(BaseModel):
    """Graham / Buffett / Modern valuations + six-value ladder."""

    graham: list[ValuationMethod] = Field(default_factory=list)
    buffett: list[ValuationMethod] = Field(default_factory=list)
    modern: list[ValuationMethod] = Field(default_factory=list)
    ladder: ValuationLadder = Field(default_factory=ValuationLadder)


class MarginOfSafetyView(BaseModel):
    """Intrinsic vs market price visualization (PRD §5.4.7)."""

    intrinsic_value: float | None = None
    market_price: float | None = None
    margin_of_safety: float | None = None
    stars: int | None = Field(default=None, ge=1, le=5)
    rating: str = ""
    detail: str = ""


class AssetLine(BaseModel):
    """One named asset or liability line (null = insufficient data)."""

    name: str
    value: float | None = None


class AssetBreakdown(BaseModel):
    """Net Asset Intelligence: assets − liabilities → adjusted vs market."""

    assets: list[AssetLine] = Field(default_factory=list)
    liabilities: list[AssetLine] = Field(default_factory=list)
    adjusted_net_assets: float | None = None
    market_cap: float | None = None
    difference_pct: float | None = None
    verdict: AssetVerdict | None = None
    detail: str = ""


class ThesisTicker(BaseModel):
    """One row of the per-stock framework + valuation table."""

    ticker: str
    list_kind: Literal["held", "watched"]
    name: str | None = None
    sector: str | None = None
    frameworks: list[FrameworkScorecard] = Field(default_factory=list)
    valuation: ValuationSet | None = None
    margin_of_safety: MarginOfSafetyView | None = None
    assets: AssetBreakdown | None = None
    # Sources that contributed to the merged snapshot (honest provenance).
    sources_used: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


class ThesisDashboard(BaseModel):
    """Thesis landing page payload (framework + valuation, T1–T2)."""

    generated_at: datetime
    generation_status: ThesisGenerationStatus = ThesisGenerationStatus.COMPLETE
    universe_count: int = 0
    tickers_considered: int = 0
    tickers: list[ThesisTicker] = Field(default_factory=list)
    frameworks: list[FrameworkId] = Field(
        default_factory=lambda: list(FrameworkId)
    )
    gaps: list[str] = Field(default_factory=list)
    empty_message: str | None = None
    disclaimer: str = PHASE0_DISCLAIMER


class ThesisGenerateRequest(BaseModel):
    """POST /api/thesis/generate body."""

    force_refresh: bool = False

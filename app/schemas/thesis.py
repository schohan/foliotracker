"""Thesis page contracts — T1: framework scorecards (Engines 2–6 surface).

Formulas and thresholds are locked in architecture.md "Framework formula
specs" (2026-08-07) before any agent consumes these scores (2B invariant).
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


class ThesisTicker(BaseModel):
    """One row of the per-stock framework score table."""

    ticker: str
    list_kind: Literal["held", "watched"]
    name: str | None = None
    sector: str | None = None
    frameworks: list[FrameworkScorecard] = Field(default_factory=list)
    # Sources that contributed to the merged snapshot (honest provenance).
    sources_used: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


class ThesisDashboard(BaseModel):
    """Thesis landing page payload (framework score table, T1)."""

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

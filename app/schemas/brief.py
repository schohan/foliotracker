"""Daily Decision Brief contracts (triage-first intelligence dashboard).

E1 (2026-08-07): optional bullet thesis linkage + morning count strip —
see architecture.md "Brief E1 enrichment specs".
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.phase0 import PHASE0_DISCLAIMER


class BriefGenerationStatus(str, Enum):
    COMPLETE = "complete"
    STALE = "stale"
    PARTIAL = "partial"


class BriefTickerStatus(str, Enum):
    OK = "ok"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


class BriefEventCategory(str, Enum):
    EARNINGS_GUIDANCE = "earnings_guidance"
    SECURITY_BREACH = "security_breach"
    CONTRACTS_WON_LOST = "contracts_won_lost"
    REGULATORY_MATERIAL = "regulatory_material"
    ANALYST_RATING = "analyst_rating"
    PRODUCT_ANNOUNCEMENT = "product_announcement"
    OTHER_MATERIAL = "other_material"
    PRICE_MOVE = "price_move"


class BriefInsightMode(str, Enum):
    DETERMINISTIC = "deterministic"
    CANNED = "canned"
    LLM = "llm"


class BriefPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"


class BriefSentiment(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class BriefMarketRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class BriefSource(BaseModel):
    """One verifiable source link for an event."""

    label: str
    url: str | None = None


class BriefInsight(BaseModel):
    """Structured triage opinion (deterministic, canned, or LLM)."""

    what_happened: str
    why: str
    market_reaction: str
    should_long_term_care: str
    confidence_label: str
    suggested_action: str
    explain_busy: str
    provider: BriefInsightMode


class BriefOpportunityScore(str, Enum):
    """Morning opportunity band (PRD §5.4.9 / E1 specs)."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class BriefBullet(BaseModel):
    """One citeable material-event bullet with triage fields."""

    text: str
    category: BriefEventCategory
    severity: int = Field(ge=1, le=5)
    evidence_ids: list[str] = Field(default_factory=list)
    source_url: str | None = None
    status: Literal["ok"] = "ok"
    # Triage enrichment
    event_key: str = ""
    impact_score: int = Field(default=0, ge=0, le=100)
    priority: BriefPriority = BriefPriority.MEDIUM
    sentiment: BriefSentiment = BriefSentiment.NEUTRAL
    headline: str = ""
    one_line_summary: str = ""
    why_it_matters: list[str] = Field(default_factory=list)
    portfolio_impact: str = ""
    suggested_action: str = ""
    confidence: int = Field(default=50, ge=0, le=100)
    sources: list[BriefSource] = Field(default_factory=list)
    insight: BriefInsight | None = None
    # E1 — thesis linkage (optional / additive)
    affected_frameworks: list[str] = Field(default_factory=list)
    thesis_impact: str | None = None


class BriefMorningCounts(BaseModel):
    """Today's Portfolio strip (PRD §5.4.9) — Thesis-backed morning counts."""

    thesis_changed: int = 0
    valuation_improved: int = 0
    mos_increased: int = 0
    balance_sheet_weakened: int = 0
    risk_increased: int = 0
    opportunity_score: BriefOpportunityScore | None = None
    thesis_available: bool = False


class QuietTicker(BaseModel):
    """Universe name with no actionable events today."""

    ticker: str
    list_kind: Literal["held", "watched"]


class BriefSummary(BaseModel):
    """Portfolio-level morning triage strip."""

    holdings_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    quiet_count: int = 0
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    themes: list[str] = Field(default_factory=list)
    market_risk: BriefMarketRisk = BriefMarketRisk.LOW
    biggest_story: str | None = None
    biggest_risk: str | None = None
    biggest_opportunity: str | None = None


class BriefTicker(BaseModel):
    """One ranked ticker row in the Brief (material gate passed or unavailable)."""

    ticker: str
    list_kind: Literal["held", "watched"]
    status: BriefTickerStatus
    daily_return: float | None = None
    move_score: int | None = Field(default=None, ge=0, le=5)
    event_severity: int | None = Field(default=None, ge=0, le=5)
    rank_score: float = 0.0
    impact_score: int = Field(default=0, ge=0, le=100)
    priority: BriefPriority | None = None
    sentiment: BriefSentiment = BriefSentiment.NEUTRAL
    headline: str | None = None
    suggested_action: str | None = None
    insight: BriefInsight | None = None
    bullets: list[BriefBullet] = Field(default_factory=list)
    # Metrics strip (display-only; from Phase0 cache / Yahoo when present)
    trailing_pe: float | None = None
    return_1y: float | None = None
    growth_score: float | None = None
    value_score: float | None = None
    risk_score: float | None = None


class DailyBrief(BaseModel):
    """Portfolio-scoped daily triage over Held ∪ Watched."""

    generated_at: datetime
    window_hours: int = 24
    generation_status: BriefGenerationStatus = BriefGenerationStatus.COMPLETE
    universe_count: int = 0
    tickers_considered: int = 0
    tickers: list[BriefTicker] = Field(default_factory=list)
    quiet_tickers: list[QuietTicker] = Field(default_factory=list)
    summary: BriefSummary | None = None
    morning: BriefMorningCounts | None = None
    insight_mode: BriefInsightMode = BriefInsightMode.DETERMINISTIC
    gaps: list[str] = Field(default_factory=list)
    empty_message: str | None = None
    disclaimer: str = PHASE0_DISCLAIMER


class BriefGenerateRequest(BaseModel):
    """Optional Generate controls."""

    force_refresh: bool = False


class BriefMissLogRequest(BaseModel):
    """Append-only dogfood miss note."""

    note: str = Field(min_length=1, max_length=2000)


class BriefExplainRequest(BaseModel):
    """On-demand Explain Like I'm Busy (uses insight provider)."""

    ticker: str
    event_key: str = ""
    category: BriefEventCategory | None = None
    text: str = ""
    daily_return: float | None = None
    list_kind: Literal["held", "watched"] = "watched"

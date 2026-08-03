"""Daily Decision Brief contracts (Slice 1)."""

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


class BriefBullet(BaseModel):
    """One citeable material-event bullet (evidence title in Slice 1)."""

    text: str
    category: BriefEventCategory
    severity: int = Field(ge=1, le=5)
    evidence_ids: list[str] = Field(default_factory=list)
    source_url: str | None = None
    status: Literal["ok"] = "ok"


class BriefTicker(BaseModel):
    """One ranked ticker row in the Brief (material gate passed or unavailable)."""

    ticker: str
    list_kind: Literal["held", "watched"]
    status: BriefTickerStatus
    daily_return: float | None = None
    move_score: int | None = Field(default=None, ge=0, le=5)
    event_severity: int | None = Field(default=None, ge=0, le=5)
    rank_score: float = 0.0
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
    gaps: list[str] = Field(default_factory=list)
    empty_message: str | None = None
    disclaimer: str = PHASE0_DISCLAIMER


class BriefGenerateRequest(BaseModel):
    """Optional Generate controls."""

    force_refresh: bool = False


class BriefMissLogRequest(BaseModel):
    """Append-only dogfood miss note."""

    note: str = Field(min_length=1, max_length=2000)

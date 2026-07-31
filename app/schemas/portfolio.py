"""Portfolio / Risk concentration contracts (Held-only v1)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.phase0 import PHASE0_DISCLAIMER, Phase0Status


class HeldPositionRisk(BaseModel):
    """One Held name under equal-weight assumption."""

    ticker: str
    weight: float = Field(ge=0.0, le=1.0)
    sector: str | None = None
    risk_score: float | None = None
    status: Phase0Status | None = None


class SectorBucket(BaseModel):
    """Aggregate equal-weight share for one sector label."""

    sector: str
    weight: float = Field(ge=0.0, le=1.0)
    count: int = Field(ge=0)
    tickers: list[str] = Field(default_factory=list)


class PortfolioRiskSnapshot(BaseModel):
    """Concentration risk for Held membership — no position sizes, no advice.

    Equal-weight: each Held ticker contributes ``1 / held_count``.
    ``partial`` when any sector or risk_score is missing (or research status
    is error/absent). Empty Held is ``ok`` with empty lists.
    """

    status: Phase0Status
    held_count: int = Field(ge=0)
    equal_weight: bool = True
    positions: list[HeldPositionRisk] = Field(default_factory=list)
    sector_buckets: list[SectorBucket] = Field(default_factory=list)
    top_name_weight: float | None = None
    avg_risk_score: float | None = None
    risk_scores_known: int = 0
    gaps: list[str] = Field(default_factory=list)
    disclaimer: str = Field(default=PHASE0_DISCLAIMER)

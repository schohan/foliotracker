"""Watchlist / portfolio dashboard contracts (local dogfood)."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

from app.schemas.phase0 import PHASE0_DISCLAIMER, Phase0Result, Phase0Status
from app.schemas.report import Scorecard


class ListKind(str, Enum):
    HELD = "held"
    WATCHED = "watched"


class WatchlistMembership(BaseModel):
    """Held vs watched ticker lists (normalized symbols)."""

    held: list[str] = Field(default_factory=list)
    watched: list[str] = Field(default_factory=list)


class WatchlistTickerSummary(BaseModel):
    """Row-level summary derived from Phase0Result — never invents metrics."""

    ticker: str
    list_kind: ListKind
    status: Phase0Status | None = None
    growth_score: float | None = None
    value_score: float | None = None
    risk_score: float | None = None
    profitability_score: float | None = None
    moat_score: float | None = None
    forward_pe: float | None = None
    thesis_one_liner: str | None = None
    conflict_count: int = 0
    cache_hit: bool | None = None
    request_id: str | None = None
    error_message: str | None = None
    updated_at: datetime | None = None


class WatchlistState(BaseModel):
    """Membership + last-known summaries for dashboard home."""

    membership: WatchlistMembership
    summaries: list[WatchlistTickerSummary] = Field(default_factory=list)
    disclaimer: str = Field(default=PHASE0_DISCLAIMER)


class WatchlistPutRequest(BaseModel):
    """Replace held/watched membership."""

    held: list[str] = Field(default_factory=list)
    watched: list[str] = Field(default_factory=list)


class WatchlistAddRequest(BaseModel):
    """Add one ticker to held or watched."""

    ticker: str
    list_kind: ListKind = ListKind.WATCHED


class BatchRefreshRequest(BaseModel):
    """Optional subset; default = all membership tickers (capped)."""

    tickers: list[str] | None = None
    max_tickers: int = Field(default=8, ge=1, le=20)


class BatchRefreshResponse(BaseModel):
    summaries: list[WatchlistTickerSummary]
    refreshed: list[str]
    skipped: list[str] = Field(default_factory=list)
    disclaimer: str = Field(default=PHASE0_DISCLAIMER)


class ResearchResponse(BaseModel):
    """Full Phase0Result wrapper for detail panel."""

    result: Phase0Result
    list_kind: ListKind | None = None


def summary_from_phase0(
    result: Phase0Result,
    *,
    list_kind: ListKind,
    updated_at: datetime | None = None,
) -> WatchlistTickerSummary:
    """Map Phase0Result → row summary. Nulls stay null."""
    sc: Scorecard | None = result.scorecard
    thesis_line = None
    if result.thesis is not None and result.thesis.thesis:
        text = result.thesis.thesis.strip()
        thesis_line = text if len(text) <= 160 else text[:159].rstrip() + "…"
    conflict_count = 0
    if result.evidence is not None:
        conflict_count = len(result.evidence.conflicts)
    forward_pe = None
    if result.fundamentals is not None:
        forward_pe = result.fundamentals.forward_pe
    return WatchlistTickerSummary(
        ticker=result.ticker,
        list_kind=list_kind,
        status=result.status,
        growth_score=sc.growth_score if sc else None,
        value_score=sc.value_score if sc else None,
        risk_score=sc.risk_score if sc else None,
        profitability_score=sc.profitability_score if sc else None,
        moat_score=sc.moat_score if sc else None,
        forward_pe=forward_pe,
        thesis_one_liner=thesis_line,
        conflict_count=conflict_count,
        cache_hit=result.cache_hit,
        request_id=result.request_id,
        error_message=result.error_message,
        updated_at=updated_at,
    )

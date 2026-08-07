"""Multi-source ingestion contracts (Phase 2C)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DataSourceConfig(BaseModel):
    """Config for one named data source."""

    source_id: str
    confidence: float = Field(ge=0.0, le=1.0)
    ttl_seconds: int = Field(ge=0)
    rate_limit_calls: int = Field(
        ge=0,
        description="Max live fetches per window; 0 = unlimited",
    )
    rate_limit_window_seconds: int = Field(ge=1, default=3600)
    rate_limit_min_interval_seconds: float = Field(
        ge=0,
        default=0,
        description=(
            "Minimum seconds between live fetches for this source; "
            "0 = allow bursts within the call count budget"
        ),
    )
    timeout_seconds: int = Field(ge=1, default=15)
    enabled: bool = True


class SourceCacheEnvelope(BaseModel):
    """On-disk envelope for a per-source cache entry."""

    source_id: str
    ticker: str
    fetched_at: datetime
    status: str = "ok"  # ok | error
    payload: dict[str, Any]


class SourceFetchMeta(BaseModel):
    """How a payload was obtained."""

    source_id: str
    cache_hit: bool = False
    stale: bool = False
    rate_limited: bool = False


class SourceFetchResult(BaseModel):
    """Result of a cached source fetch; ``data`` is a validated domain model."""

    data: Any
    meta: SourceFetchMeta

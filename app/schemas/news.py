"""News and sentiment schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class NewsSummary(BaseModel):
    ticker: str
    headlines: list[str] = Field(default_factory=list)
    summary: str | None = None
    sentiment: str | None = None
    sentiment_score: float | None = Field(default=None, ge=-1.0, le=1.0)

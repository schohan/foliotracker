"""Competitor analysis schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CompetitorAnalysis(BaseModel):
    ticker: str
    competitors: list[str] = Field(default_factory=list)
    summary: str | None = None
    relative_position: str | None = None

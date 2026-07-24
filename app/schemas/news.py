"""News and sentiment schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class NewsArticle(BaseModel):
    """Single news article from a news tool."""

    title: str
    url: str
    published_at: datetime | None = None
    publisher: str | None = None


class NewsBatch(BaseModel):
    """Batch of news articles for a ticker."""

    ticker: str
    articles: list[NewsArticle] = Field(default_factory=list)


class NewsSummary(BaseModel):
    ticker: str
    headlines: list[str] = Field(default_factory=list)
    summary: str | None = None
    sentiment: str | None = None
    sentiment_score: float | None = Field(default=None, ge=-1.0, le=1.0)

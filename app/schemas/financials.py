"""Financial-domain schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class FinancialMetrics(BaseModel):
    ticker: str
    market_cap: float | None = None
    revenue_growth: float | None = None
    gross_margin: float | None = None
    operating_margin: float | None = None
    free_cash_flow: float | None = None
    debt_to_equity: float | None = None
    pe_ratio: float | None = None


class RevenueHistory(BaseModel):
    ticker: str
    periods: list[str] = Field(default_factory=list)
    revenues: list[float] = Field(default_factory=list)


class RiskFactors(BaseModel):
    ticker: str
    factors: list[str] = Field(default_factory=list)

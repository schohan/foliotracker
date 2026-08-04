"""Financial-domain schemas (Phase 2C.2 enriched fundamentals)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CompanyProfile(BaseModel):
    """Issuer profile from a market-data source."""

    name: str | None = None
    sector: str | None = None
    industry: str | None = None
    summary: str | None = None


class PriceReturns(BaseModel):
    """Price performance fractions (0.10 = +10%)."""

    return_3m: float | None = None
    return_1y: float | None = None
    return_ytd: float | None = None


class PeriodMetric(BaseModel):
    """One period in a time series (revenue, earnings, etc.)."""

    period: str
    value: float | None = None


class StatementSummary(BaseModel):
    """Latest available statement snapshot (period end)."""

    as_of: str | None = None
    total_revenue: float | None = None
    net_income: float | None = None
    total_assets: float | None = None
    total_liabilities: float | None = None
    total_cash: float | None = None
    total_debt: float | None = None
    operating_cashflow: float | None = None
    free_cash_flow: float | None = None


class FieldProvenance(BaseModel):
    """Which source filled a field on the merged snapshot."""

    source_id: str
    as_of: datetime | None = None


class FinancialMetrics(BaseModel):
    """Enriched fundamentals for one ticker (multi-source via merge in 2C.3).

    ``pe_ratio`` remains the scoring input (trailing preferred). Trailing and
    forward P/E are also stored explicitly when available.
    ``field_provenance`` maps dotted field paths → source (merge output).
    """

    ticker: str
    # Core Phase 0 fields
    market_cap: float | None = None
    revenue_growth: float | None = None
    gross_margin: float | None = None
    operating_margin: float | None = None
    free_cash_flow: float | None = None
    debt_to_equity: float | None = None
    pe_ratio: float | None = None
    # 2C.2 enrichment
    trailing_pe: float | None = None
    forward_pe: float | None = None
    eps_trailing: float | None = None
    eps_forward: float | None = None
    earnings_growth: float | None = None
    return_on_equity: float | None = None
    current_ratio: float | None = None
    total_cash: float | None = None
    total_debt: float | None = None
    # Yahoo stats page — valuation / profitability (brief + watchlist)
    enterprise_value: float | None = None
    peg_ratio: float | None = None
    price_to_sales: float | None = None
    price_to_book: float | None = None
    ev_to_revenue: float | None = None
    ev_to_ebitda: float | None = None
    profit_margin: float | None = None
    return_on_assets: float | None = None
    revenue_ttm: float | None = None
    net_income_ttm: float | None = None
    profile: CompanyProfile | None = None
    returns: PriceReturns | None = None
    revenue_history: list[PeriodMetric] = Field(default_factory=list)
    earnings_history: list[PeriodMetric] = Field(default_factory=list)
    balance_sheet: StatementSummary | None = None
    cash_flow: StatementSummary | None = None
    # Daily closes for Risk/Brief (Yahoo source-cache); not used in evidence IDs.
    history_closes: list[tuple[str, float]] = Field(default_factory=list)
    source_id: str = "yahoo"
    as_of: datetime | None = None
    field_provenance: dict[str, FieldProvenance] = Field(default_factory=dict)


# Phase 2C name for the enriched metrics contract (same model for now).
FundamentalsSnapshot = FinancialMetrics


class RevenueHistory(BaseModel):
    ticker: str
    periods: list[str] = Field(default_factory=list)
    revenues: list[float] = Field(default_factory=list)


class RiskFactors(BaseModel):
    ticker: str
    factors: list[str] = Field(default_factory=list)

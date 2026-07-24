"""SEC filings schemas."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class SecFiling(BaseModel):
    """Single SEC EDGAR filing (metadata only)."""

    form: str
    filing_date: date | None = None
    report_date: date | None = None
    accession_number: str
    primary_document: str | None = None
    url: str


class SecFilingsBatch(BaseModel):
    """Recent SEC filings for a ticker."""

    ticker: str
    cik: str
    company_name: str | None = None
    filings: list[SecFiling] = Field(default_factory=list)

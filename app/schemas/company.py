"""Company-domain schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CompanyProfile(BaseModel):
    ticker: str
    name: str
    sector: str | None = None
    industry: str | None = None
    description: str | None = None
    headquarters: str | None = None
    employees: int | None = None
    website: str | None = None


class ManagementSummary(BaseModel):
    ticker: str
    ceo: str | None = None
    key_executives: list[str] = Field(default_factory=list)
    notes: str | None = None


class MoatAssessment(BaseModel):
    ticker: str
    moat_type: str | None = None
    strength: float | None = Field(default=None, ge=0.0, le=1.0)
    rationale: str | None = None

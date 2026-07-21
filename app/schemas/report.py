"""Report and investment thesis schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class ThesisClaim(BaseModel):
    """Material assertion that must cite at least one evidence id."""

    text: str
    evidence_ids: list[str] = Field(min_length=1)


class InvestmentThesis(BaseModel):
    ticker: str
    thesis: str
    claims: list[ThesisClaim] = Field(default_factory=list)
    bull_case: str | None = None
    bear_case: str | None = None
    key_risks: list[str] = Field(default_factory=list)
    conviction: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence_ids: list[str] = Field(
        default_factory=list,
        description="Union of all claim evidence_ids",
    )

    @model_validator(mode="after")
    def sync_evidence_ids(self) -> InvestmentThesis:
        claimed = []
        for claim in self.claims:
            claimed.extend(claim.evidence_ids)
        # Preserve explicit evidence_ids if set; else derive from claims
        if not self.evidence_ids and claimed:
            self.evidence_ids = list(dict.fromkeys(claimed))
        return self


class Scorecard(BaseModel):
    ticker: str
    growth_score: float | None = None
    value_score: float | None = None
    profitability_score: float | None = None
    moat_score: float | None = None
    risk_score: float | None = None
    execution_score: float | None = None


class ResearchReport(BaseModel):
    ticker: str
    thesis: InvestmentThesis | None = None
    scorecard: Scorecard | None = None
    summary: str | None = None
    raw_json: dict | None = None

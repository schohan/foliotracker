"""Phase 0 pipeline result contract."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator

from app.schemas.evidence import EvidenceBundle
from app.schemas.report import InvestmentThesis

PHASE0_DISCLAIMER = (
    "FolioTracker output is for informational and educational purposes only. "
    "It is not investment, legal, or tax advice. Do your own research."
)


class Phase0Status(str, Enum):
    OK = "ok"
    PARTIAL = "partial"
    ERROR = "error"


class Phase0Result(BaseModel):
    """End-to-end Phase 0 response — always includes disclaimer, cache_hit, request_id."""

    ticker: str
    status: Phase0Status
    evidence: EvidenceBundle | None = None
    thesis: InvestmentThesis | None = None
    error_message: str | None = None
    disclaimer: str = Field(default=PHASE0_DISCLAIMER)
    cache_hit: bool = False
    request_id: str

    @model_validator(mode="after")
    def check_citation_invariant(self) -> Phase0Result:
        if self.status in (Phase0Status.OK, Phase0Status.PARTIAL) and self.thesis:
            if self.evidence is None:
                raise ValueError("thesis requires evidence bundle when status is ok/partial")
            known = {item.id for item in self.evidence.items}
            for claim in self.thesis.claims:
                missing = set(claim.evidence_ids) - known
                if missing:
                    raise ValueError(
                        f"dangling evidence_ids on claim: {sorted(missing)}"
                    )
            dangling = set(self.thesis.evidence_ids) - known
            if dangling:
                raise ValueError(
                    f"dangling evidence_ids on thesis: {sorted(dangling)}"
                )
        return self


def assert_claims_cite_bundle(
    thesis: InvestmentThesis, bundle: EvidenceBundle
) -> None:
    """Raise ValueError if any claim cites an id not in the bundle."""
    known = {item.id for item in bundle.items}
    for claim in thesis.claims:
        missing = set(claim.evidence_ids) - known
        if missing:
            raise ValueError(f"dangling evidence_ids: {sorted(missing)}")

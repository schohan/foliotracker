"""Thesis validation and empty-claims failure path."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.agents.report.thesis_agent import (
    DanglingCitationError,
    EmptyClaimsError,
    generate_thesis,
)
from app.schemas.evidence import BundleStatus, Evidence, EvidenceBundle
from app.schemas.phase0 import Phase0ErrorCode
from app.schemas.report import InvestmentThesis, ThesisClaim


def _bundle() -> EvidenceBundle:
    return EvidenceBundle(
        ticker="NVDA",
        status=BundleStatus.OK,
        items=[
            Evidence(
                id="ev_financial_NVDA_1",
                type="financial",
                source="Yahoo Finance",
                confidence=0.95,
                timestamp=datetime.now(timezone.utc),
                citation="https://finance.yahoo.com/quote/NVDA",
                data={"revenue_growth": 0.18},
            )
        ],
    )


def test_generate_thesis_empty_claims_raises_empty_claims_error() -> None:
    prompts: list[str] = []

    def empty_model(prompt: str) -> str:
        prompts.append(prompt)
        return InvestmentThesis(
            ticker="NVDA",
            thesis="No claims.",
            claims=[],
        ).model_dump_json()

    with pytest.raises(EmptyClaimsError) as exc_info:
        generate_thesis(_bundle(), model_caller=empty_model)
    assert exc_info.value.error_code == Phase0ErrorCode.THESIS_EMPTY_CLAIMS
    assert len(prompts) == 2
    assert "PREVIOUS OUTPUT FAILED" in prompts[1]
    assert "Do not return an empty claims list" in prompts[1]


def test_repair_prompt_forbids_empty_claims() -> None:
    from app.agents.report.thesis_agent import _build_prompt

    prompt = _build_prompt(_bundle(), repair=True)
    assert "Do not return an empty claims list" in prompt
    assert "at least one" in prompt


def test_generate_thesis_dangling_raises() -> None:
    def dangling_model(prompt: str) -> str:
        return InvestmentThesis(
            ticker="NVDA",
            thesis="Bad.",
            claims=[
                ThesisClaim(text="Fake.", evidence_ids=["ev_missing"]),
            ],
        ).model_dump_json()

    with pytest.raises(DanglingCitationError) as exc_info:
        generate_thesis(_bundle(), model_caller=dangling_model)
    assert exc_info.value.error_code == Phase0ErrorCode.THESIS_DANGLING_CITATION

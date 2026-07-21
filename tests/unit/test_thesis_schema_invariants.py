"""Phase 0 schema invariants — runnable now (no I/O, no LLM)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.evidence import BundleStatus, Evidence, EvidenceBundle
from app.schemas.phase0 import (
    PHASE0_DISCLAIMER,
    Phase0Result,
    Phase0Status,
    assert_claims_cite_bundle,
)
from app.schemas.report import InvestmentThesis, ThesisClaim


def _bundle(*ids: str) -> EvidenceBundle:
    return EvidenceBundle(
        ticker="NVDA",
        status=BundleStatus.OK,
        items=[
            Evidence(
                id=eid,
                type="financial",
                source="Yahoo Finance",
                confidence=0.95,
                timestamp=datetime.now(timezone.utc),
                citation="https://finance.yahoo.com/quote/NVDA",
                data={"revenue_growth": 0.18},
            )
            for eid in ids
        ],
    )


def test_thesis_claim_requires_evidence_ids() -> None:
    with pytest.raises(ValidationError):
        ThesisClaim(text="Revenue grew", evidence_ids=[])


def test_assert_claims_cite_bundle_ok() -> None:
    bundle = _bundle("ev_financial_NVDA_1")
    thesis = InvestmentThesis(
        ticker="NVDA",
        thesis="Growth remains strong.",
        claims=[
            ThesisClaim(
                text="Revenue growth is 18%.",
                evidence_ids=["ev_financial_NVDA_1"],
            )
        ],
    )
    assert_claims_cite_bundle(thesis, bundle)
    assert "ev_financial_NVDA_1" in thesis.evidence_ids


def test_assert_claims_cite_bundle_dangling() -> None:
    bundle = _bundle("ev_financial_NVDA_1")
    thesis = InvestmentThesis(
        ticker="NVDA",
        thesis="Made up.",
        claims=[
            ThesisClaim(text="Invented metric.", evidence_ids=["ev_missing"])
        ],
    )
    with pytest.raises(ValueError, match="dangling"):
        assert_claims_cite_bundle(thesis, bundle)


def test_phase0_result_requires_request_id_and_disclaimer() -> None:
    result = Phase0Result(
        ticker="NVDA",
        status=Phase0Status.ERROR,
        error_message="not found",
        request_id="req-1",
        cache_hit=False,
    )
    assert result.disclaimer == PHASE0_DISCLAIMER
    assert result.request_id == "req-1"
    assert result.cache_hit is False


def test_phase0_result_rejects_dangling_citations_on_ok() -> None:
    bundle = _bundle("ev_financial_NVDA_1")
    thesis = InvestmentThesis(
        ticker="NVDA",
        thesis="Bad cite.",
        claims=[
            ThesisClaim(text="Uses missing id.", evidence_ids=["ev_missing"])
        ],
    )
    with pytest.raises(ValidationError):
        Phase0Result(
            ticker="NVDA",
            status=Phase0Status.OK,
            evidence=bundle,
            thesis=thesis,
            request_id="req-2",
            cache_hit=False,
        )


def test_phase0_result_ok_with_valid_citations() -> None:
    bundle = _bundle("ev_financial_NVDA_1")
    thesis = InvestmentThesis(
        ticker="NVDA",
        thesis="Solid financials.",
        claims=[
            ThesisClaim(
                text="Revenue growth is elevated.",
                evidence_ids=["ev_financial_NVDA_1"],
            )
        ],
    )
    result = Phase0Result(
        ticker="NVDA",
        status=Phase0Status.OK,
        evidence=bundle,
        thesis=thesis,
        request_id="req-3",
        cache_hit=False,
    )
    assert result.status == Phase0Status.OK
    assert result.cache_hit is False


def test_phase0_error_still_has_disclaimer_and_ids() -> None:
    result = Phase0Result(
        ticker="ZZZZ",
        status=Phase0Status.ERROR,
        error_message="TickerNotFoundError",
        request_id="req-err",
        cache_hit=False,
    )
    assert result.disclaimer
    assert result.request_id
    assert result.thesis is None

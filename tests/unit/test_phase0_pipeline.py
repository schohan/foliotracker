"""Phase 0 pipeline with mocked Yahoo + thesis (no live network/LLM)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.configs.settings import Settings
from app.schemas.financials import FinancialMetrics
from app.schemas.phase0 import Phase0Status
from app.schemas.report import InvestmentThesis, ThesisClaim
from app.services import phase0_pipeline as pipe
from app.services.evidence import evidence_from_metrics
from app.services.phase0_pipeline import run_phase0_research


def _metrics() -> FinancialMetrics:
    return FinancialMetrics(
        ticker="NVDA",
        market_cap=1e12,
        revenue_growth=0.18,
        pe_ratio=40.0,
        gross_margin=0.7,
    )


def test_pipeline_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        pipe,
        "settings",
        Settings(
            google_api_key=None,
            phase0_cache_dir=tmp_path,
            phase0_cache_ttl_seconds=3600,
            yahoo_timeout_seconds=15,
        ),
    )
    monkeypatch.setattr(pipe, "fetch_financial_metrics", lambda ticker, **k: _metrics())

    def fake_model(prompt: str) -> str:
        ev = evidence_from_metrics(_metrics())
        thesis = InvestmentThesis(
            ticker="NVDA",
            thesis="Growth is strong.",
            claims=[
                ThesisClaim(
                    text="Revenue growth is 18%.",
                    evidence_ids=[ev.id],
                )
            ],
        )
        return thesis.model_dump_json()

    result = run_phase0_research("nvda", model_caller=fake_model, skip_cache=True)
    assert result.status in (Phase0Status.OK, Phase0Status.PARTIAL)
    assert result.cache_hit is False
    assert result.thesis is not None
    assert result.disclaimer
    assert result.request_id
    assert result.evidence is not None

    result2 = run_phase0_research("NVDA", model_caller=fake_model, skip_cache=False)
    assert result2.cache_hit is True
    assert result2.request_id != result.request_id


def test_pipeline_invalid_ticker() -> None:
    result = run_phase0_research("bad ticker!")
    assert result.status == Phase0Status.ERROR
    assert result.disclaimer
    assert result.request_id

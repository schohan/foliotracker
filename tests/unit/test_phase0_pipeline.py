"""Phase 0/1/2A pipeline with mocked Yahoo + news + SEC + thesis."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from app.configs.settings import Settings
from app.schemas.filings import SecFiling, SecFilingsBatch
from app.schemas.financials import FinancialMetrics
from app.schemas.news import NewsArticle, NewsBatch
from app.schemas.phase0 import Phase0Status
from app.schemas.report import InvestmentThesis, ThesisClaim
from app.services import phase0_pipeline as pipe
from app.services.evidence import (
    evidence_from_filings,
    evidence_from_metrics,
    evidence_from_news,
)
from app.services.phase0_pipeline import run_phase0_research
from app.tools.filings.sec_edgar import ToolTimeoutError as SecTimeoutError
from app.tools.news.google_news import ToolTimeoutError as NewsTimeoutError


def _metrics() -> FinancialMetrics:
    return FinancialMetrics(
        ticker="NVDA",
        market_cap=1e12,
        revenue_growth=0.18,
        pe_ratio=40.0,
        gross_margin=0.7,
        operating_margin=0.55,
        free_cash_flow=2.5e10,
        debt_to_equity=0.2,
    )


def _news() -> NewsBatch:
    return NewsBatch(
        ticker="NVDA",
        articles=[
            NewsArticle(
                title="NVDA growth continues as AI demand stays strong",
                url="https://example.com/nvda-news",
                published_at=datetime(2026, 7, 20, tzinfo=timezone.utc),
                publisher="Example",
            )
        ],
    )


def _filings() -> SecFilingsBatch:
    return SecFilingsBatch(
        ticker="NVDA",
        cik="0001045810",
        company_name="NVIDIA CORP",
        filings=[
            SecFiling(
                form="10-K",
                filing_date=date(2026, 2, 26),
                report_date=date(2026, 1, 26),
                accession_number="0001045810-26-000055",
                primary_document="nvda-20260126.htm",
                url="https://www.sec.gov/Archives/edgar/data/1045810/000104581026000055/",
            )
        ],
    )


def _patch_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        pipe,
        "settings",
        Settings(
            google_api_key=None,
            phase0_cache_dir=tmp_path,
            phase0_cache_ttl_seconds=3600,
            yahoo_timeout_seconds=15,
            news_timeout_seconds=15,
            news_max_articles=5,
            sec_timeout_seconds=15,
            sec_max_filings=5,
        ),
    )


def test_pipeline_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_settings(monkeypatch, tmp_path)
    monkeypatch.setattr(pipe, "fetch_financial_metrics", lambda ticker, **k: _metrics())
    monkeypatch.setattr(pipe, "fetch_google_news", lambda ticker, **k: _news())
    monkeypatch.setattr(pipe, "fetch_sec_filings", lambda ticker, **k: _filings())

    def fake_model(prompt: str) -> str:
        fin = evidence_from_metrics(_metrics())
        news_items = evidence_from_news(_news())
        sec_items = evidence_from_filings(_filings())
        thesis = InvestmentThesis(
            ticker="NVDA",
            thesis="Growth is strong.",
            claims=[
                ThesisClaim(
                    text="Revenue growth is 18%.",
                    evidence_ids=[fin.id],
                ),
                ThesisClaim(
                    text="News notes continued AI demand.",
                    evidence_ids=[news_items[0].id],
                ),
                ThesisClaim(
                    text="Latest 10-K is on file with the SEC.",
                    evidence_ids=[sec_items[0].id],
                ),
            ],
        )
        return thesis.model_dump_json()

    result = run_phase0_research("nvda", model_caller=fake_model, skip_cache=True)
    assert result.status == Phase0Status.OK
    assert result.cache_hit is False
    assert result.thesis is not None
    assert result.disclaimer
    assert result.request_id
    assert result.evidence is not None
    assert len(result.evidence.items) >= 3
    assert any(i.type == "sec" for i in result.evidence.items)
    assert result.evidence.conflicts == []

    result2 = run_phase0_research("NVDA", model_caller=fake_model, skip_cache=False)
    assert result2.cache_hit is True
    assert result2.request_id != result.request_id


def test_pipeline_news_timeout_yields_partial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_settings(monkeypatch, tmp_path)
    monkeypatch.setattr(pipe, "fetch_financial_metrics", lambda ticker, **k: _metrics())
    monkeypatch.setattr(pipe, "fetch_sec_filings", lambda ticker, **k: _filings())

    def boom(ticker: str, **k):
        raise NewsTimeoutError("timeout")

    monkeypatch.setattr(pipe, "fetch_google_news", boom)

    def fake_model(prompt: str) -> str:
        fin = evidence_from_metrics(_metrics())
        sec_items = evidence_from_filings(_filings())
        thesis = InvestmentThesis(
            ticker="NVDA",
            thesis="Financials and filings only.",
            claims=[
                ThesisClaim(text="Revenue growth is 18%.", evidence_ids=[fin.id]),
                ThesisClaim(text="10-K is on file.", evidence_ids=[sec_items[0].id]),
            ],
        )
        return thesis.model_dump_json()

    result = run_phase0_research("NVDA", model_caller=fake_model, skip_cache=True)
    assert result.status == Phase0Status.PARTIAL
    assert result.evidence is not None
    assert any(i.type == "financial" for i in result.evidence.items)
    assert any(i.type == "sec" for i in result.evidence.items)
    assert not any(i.type == "news" for i in result.evidence.items)
    assert result.thesis is not None
    assert result.error_message is None


def test_pipeline_sec_timeout_yields_partial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_settings(monkeypatch, tmp_path)
    monkeypatch.setattr(pipe, "fetch_financial_metrics", lambda ticker, **k: _metrics())
    monkeypatch.setattr(pipe, "fetch_google_news", lambda ticker, **k: _news())

    def boom(ticker: str, **k):
        raise SecTimeoutError("timeout")

    monkeypatch.setattr(pipe, "fetch_sec_filings", boom)

    def fake_model(prompt: str) -> str:
        fin = evidence_from_metrics(_metrics())
        news_items = evidence_from_news(_news())
        thesis = InvestmentThesis(
            ticker="NVDA",
            thesis="Financials and news only.",
            claims=[
                ThesisClaim(text="Revenue growth is 18%.", evidence_ids=[fin.id]),
                ThesisClaim(
                    text="News notes AI demand.", evidence_ids=[news_items[0].id]
                ),
            ],
        )
        return thesis.model_dump_json()

    result = run_phase0_research("NVDA", model_caller=fake_model, skip_cache=True)
    assert result.status == Phase0Status.PARTIAL
    assert result.evidence is not None
    assert not any(i.type == "sec" for i in result.evidence.items)
    assert result.thesis is not None


def test_pipeline_invalid_ticker() -> None:
    result = run_phase0_research("bad ticker!")
    assert result.status == Phase0Status.ERROR
    assert result.disclaimer
    assert result.request_id

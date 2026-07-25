"""Phase 0/1/2A/2C.3 pipeline with mocked Yahoo + news + SEC + XBRL + thesis."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from app.configs.settings import Settings
from app.schemas.filings import SecFiling, SecFilingsBatch
from app.schemas.financials import FinancialMetrics, PeriodMetric, StatementSummary
from app.schemas.news import NewsArticle, NewsBatch
from app.schemas.phase0 import Phase0ErrorCode, Phase0Status
from app.schemas.report import InvestmentThesis, ThesisClaim
from app.services import phase0_pipeline as pipe
from app.services.phase0_pipeline import run_phase0_research
from app.tools.filings.sec_edgar import ToolTimeoutError as SecTimeoutError
from app.tools.filings.sec_xbrl import ToolTimeoutError as XbrlTimeoutError
from app.tools.finance.yahoo_finance import ToolUpstreamError as YahooUpstreamError
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
        source_id="yahoo",
    )


def _min_fundamentals(*, source_id: str = "sec_xbrl") -> FinancialMetrics:
    """Snapshot that satisfies MINIMUM_FUNDAMENTALS_FIELD_PATHS."""
    bs = StatementSummary(
        as_of="2024-12-31",
        total_revenue=100.0,
        total_assets=500.0,
        total_liabilities=200.0,
        total_cash=50.0,
        total_debt=80.0,
    )
    return FinancialMetrics(
        ticker="NVDA",
        gross_margin=0.4,
        operating_margin=0.3,
        total_debt=80.0,
        total_cash=50.0,
        eps_trailing=6.5,
        earnings_history=[PeriodMetric(period="2024Q4", value=1.5)],
        balance_sheet=bs,
        cash_flow=StatementSummary(as_of="2024-12-31", operating_cashflow=10.0),
        source_id=source_id,
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
            source_cache_dir=tmp_path / "sources",
            yahoo_timeout_seconds=15,
            news_timeout_seconds=15,
            news_max_articles=5,
            sec_timeout_seconds=15,
            sec_xbrl_timeout_seconds=30,
            sec_max_filings=5,
        ),
    )


def _patch_xbrl_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(ticker: str, **k):
        raise XbrlTimeoutError("xbrl timeout")

    monkeypatch.setattr(pipe, "fetch_sec_xbrl_fundamentals", boom)


def _thesis_from_bundle(bundle, thesis: str = "Growth is strong.", **_kwargs):
    ids = [i.id for i in bundle.items]
    claims = [
        ThesisClaim(text=f"Claim on {i.type}.", evidence_ids=[i.id])
        for i in bundle.items[:3]
    ]
    if not claims and ids:
        claims = [ThesisClaim(text="Fallback claim.", evidence_ids=[ids[0]])]
    return InvestmentThesis(ticker="NVDA", thesis=thesis, claims=claims)


def test_pipeline_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_settings(monkeypatch, tmp_path)
    _patch_xbrl_fail(monkeypatch)
    monkeypatch.setattr(pipe, "fetch_financial_metrics", lambda ticker, **k: _metrics())
    monkeypatch.setattr(pipe, "fetch_google_news", lambda ticker, **k: _news())
    monkeypatch.setattr(pipe, "fetch_sec_filings", lambda ticker, **k: _filings())
    monkeypatch.setattr(pipe, "generate_thesis", _thesis_from_bundle)

    result = run_phase0_research("nvda", skip_cache=True)
    assert result.status == Phase0Status.OK
    assert result.cache_hit is False
    assert result.thesis is not None
    assert result.disclaimer
    assert result.request_id
    assert result.evidence is not None
    assert len(result.evidence.items) >= 3
    assert any(i.type == "sec" for i in result.evidence.items)
    assert result.evidence.conflicts == []
    assert result.fundamentals is not None
    assert result.fundamentals.ticker == "NVDA"
    assert result.fundamentals.pe_ratio == 40.0
    assert result.scorecard is not None
    assert result.scorecard.ticker == "NVDA"
    assert result.scorecard.growth_score is not None
    assert result.scorecard.execution_score is None

    result2 = run_phase0_research("NVDA", skip_cache=False)
    assert result2.cache_hit is True
    assert result2.request_id != result.request_id
    assert result2.scorecard is not None
    assert result2.scorecard.growth_score == result.scorecard.growth_score


def test_pipeline_news_timeout_yields_partial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_settings(monkeypatch, tmp_path)
    _patch_xbrl_fail(monkeypatch)
    monkeypatch.setattr(pipe, "fetch_financial_metrics", lambda ticker, **k: _metrics())
    monkeypatch.setattr(pipe, "fetch_sec_filings", lambda ticker, **k: _filings())

    def boom(ticker: str, **k):
        raise NewsTimeoutError("timeout")

    monkeypatch.setattr(pipe, "fetch_google_news", boom)
    monkeypatch.setattr(
        pipe,
        "generate_thesis",
        lambda bundle, **k: _thesis_from_bundle(
            bundle, thesis="Financials and filings only."
        ),
    )

    result = run_phase0_research("NVDA", skip_cache=True)
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
    _patch_xbrl_fail(monkeypatch)
    monkeypatch.setattr(pipe, "fetch_financial_metrics", lambda ticker, **k: _metrics())
    monkeypatch.setattr(pipe, "fetch_google_news", lambda ticker, **k: _news())

    def boom(ticker: str, **k):
        raise SecTimeoutError("timeout")

    monkeypatch.setattr(pipe, "fetch_sec_filings", boom)
    monkeypatch.setattr(
        pipe,
        "generate_thesis",
        lambda bundle, **k: _thesis_from_bundle(
            bundle, thesis="Financials and news only."
        ),
    )

    result = run_phase0_research("NVDA", skip_cache=True)
    assert result.status == Phase0Status.PARTIAL
    assert result.evidence is not None
    assert not any(i.type == "sec" for i in result.evidence.items)
    assert result.thesis is not None


def test_pipeline_invalid_ticker() -> None:
    result = run_phase0_research("bad ticker!")
    assert result.status == Phase0Status.ERROR
    assert result.disclaimer
    assert result.request_id
    assert result.error_code == Phase0ErrorCode.INVALID_TICKER.value


def test_pipeline_thesis_empty_claims_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_settings(monkeypatch, tmp_path)
    _patch_xbrl_fail(monkeypatch)
    monkeypatch.setattr(pipe, "fetch_financial_metrics", lambda ticker, **k: _metrics())
    monkeypatch.setattr(pipe, "fetch_google_news", lambda ticker, **k: _news())
    monkeypatch.setattr(pipe, "fetch_sec_filings", lambda ticker, **k: _filings())

    def empty_claims_model(prompt: str) -> str:
        return InvestmentThesis(
            ticker="NVDA",
            thesis="Unable to form claims.",
            claims=[],
        ).model_dump_json()

    result = run_phase0_research(
        "NVDA", model_caller=empty_claims_model, skip_cache=True
    )
    assert result.status == Phase0Status.ERROR
    assert result.error_code == Phase0ErrorCode.THESIS_EMPTY_CLAIMS.value
    assert result.thesis is None
    assert result.evidence is not None
    assert len(result.evidence.items) >= 1
    assert result.fundamentals is not None
    assert result.fundamentals.pe_ratio == 40.0
    assert result.error_message is not None
    assert "UncitedClaimError" not in result.error_message
    assert "EmptyClaimsError" not in result.error_message
    assert "no material claims" in result.error_message
    assert result.request_id in result.error_message
    assert "Evidence is included" in result.error_message


def test_pipeline_thesis_dangling_citation_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_settings(monkeypatch, tmp_path)
    _patch_xbrl_fail(monkeypatch)
    monkeypatch.setattr(pipe, "fetch_financial_metrics", lambda ticker, **k: _metrics())
    monkeypatch.setattr(pipe, "fetch_google_news", lambda ticker, **k: _news())
    monkeypatch.setattr(pipe, "fetch_sec_filings", lambda ticker, **k: _filings())

    def dangling_model(prompt: str) -> str:
        return InvestmentThesis(
            ticker="NVDA",
            thesis="Invented cite.",
            claims=[
                ThesisClaim(
                    text="Uses a fake evidence id.",
                    evidence_ids=["ev_missing_not_in_bundle"],
                )
            ],
        ).model_dump_json()

    result = run_phase0_research("NVDA", model_caller=dangling_model, skip_cache=True)
    assert result.status == Phase0Status.ERROR
    assert result.error_code == Phase0ErrorCode.THESIS_DANGLING_CITATION.value
    assert result.thesis is None
    assert result.evidence is not None
    assert result.error_message is not None
    assert "DanglingCitationError" not in result.error_message
    assert "not in the bundle" in result.error_message
    assert result.request_id in result.error_message


def test_pipeline_yahoo_fail_xbrl_min_set_softens_to_partial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_settings(monkeypatch, tmp_path)
    monkeypatch.setattr(pipe, "fetch_google_news", lambda ticker, **k: _news())
    monkeypatch.setattr(pipe, "fetch_sec_filings", lambda ticker, **k: _filings())
    monkeypatch.setattr(
        pipe, "fetch_sec_xbrl_fundamentals", lambda ticker, **k: _min_fundamentals()
    )

    def boom(ticker: str, **k):
        raise YahooUpstreamError("yahoo down")

    monkeypatch.setattr(pipe, "fetch_financial_metrics", boom)

    def fake_thesis(bundle, **kwargs):
        ids = [i.id for i in bundle.items]
        return InvestmentThesis(
            ticker="NVDA",
            thesis="Recovered via SEC XBRL.",
            claims=[
                ThesisClaim(text="Fundamentals recovered.", evidence_ids=[ids[0]]),
            ],
        )

    monkeypatch.setattr(pipe, "generate_thesis", fake_thesis)

    result = run_phase0_research("NVDA", skip_cache=True)
    assert result.status == Phase0Status.PARTIAL
    assert result.thesis is not None
    assert result.fundamentals is not None
    assert result.fundamentals.eps_trailing == 6.5
    assert result.fundamentals.balance_sheet is not None
    assert result.fundamentals.field_provenance


def test_pipeline_yahoo_fail_without_min_set_still_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_settings(monkeypatch, tmp_path)
    _patch_xbrl_fail(monkeypatch)
    monkeypatch.setattr(pipe, "fetch_google_news", lambda ticker, **k: _news())
    monkeypatch.setattr(pipe, "fetch_sec_filings", lambda ticker, **k: _filings())

    def boom(ticker: str, **k):
        raise YahooUpstreamError("yahoo down")

    monkeypatch.setattr(pipe, "fetch_financial_metrics", boom)

    result = run_phase0_research("NVDA", skip_cache=True)
    assert result.status == Phase0Status.ERROR
    assert result.error_code == Phase0ErrorCode.DATA_FETCH_FAILED.value
    assert result.thesis is None

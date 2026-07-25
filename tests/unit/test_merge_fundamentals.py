"""merge_fundamentals fill-nulls, trust, conflicts."""

from __future__ import annotations

from app.schemas.financials import (
    CompanyProfile,
    FinancialMetrics,
    PeriodMetric,
    PriceReturns,
    StatementSummary,
)
from app.services.merge_fundamentals import (
    ProviderSnapshot,
    merge_fundamentals,
    trust_rank,
)
from app.services.source_registry import (
    SOURCE_ALPHA_VANTAGE,
    SOURCE_SEC_XBRL,
    SOURCE_YAHOO,
)


def test_trust_rank_prefers_sec_for_statements() -> None:
    assert trust_rank(SOURCE_SEC_XBRL, "balance_sheet.total_assets") > trust_rank(
        SOURCE_YAHOO, "balance_sheet.total_assets"
    )
    assert trust_rank(SOURCE_YAHOO, "balance_sheet.total_assets") > trust_rank(
        SOURCE_ALPHA_VANTAGE, "balance_sheet.total_assets"
    )
    assert trust_rank(SOURCE_YAHOO, "pe_ratio") > trust_rank(
        SOURCE_ALPHA_VANTAGE, "pe_ratio"
    )
    assert trust_rank(SOURCE_ALPHA_VANTAGE, "forward_pe") > trust_rank(
        SOURCE_SEC_XBRL, "forward_pe"
    )


def test_fill_nulls_from_sec() -> None:
    yahoo = FinancialMetrics(
        ticker="AAPL",
        pe_ratio=25.0,
        forward_pe=22.0,
        source_id=SOURCE_YAHOO,
    )
    sec = FinancialMetrics(
        ticker="AAPL",
        eps_trailing=6.5,
        total_cash=50.0,
        balance_sheet=StatementSummary(total_assets=500.0, total_cash=50.0),
        source_id=SOURCE_SEC_XBRL,
    )
    result = merge_fundamentals(
        [
            ProviderSnapshot(SOURCE_YAHOO, yahoo),
            ProviderSnapshot(SOURCE_SEC_XBRL, sec),
        ],
        ticker="AAPL",
    )
    assert result.snapshot.pe_ratio == 25.0
    assert result.snapshot.eps_trailing == 6.5
    assert result.snapshot.balance_sheet is not None
    assert result.snapshot.balance_sheet.total_assets == 500.0
    assert result.snapshot.field_provenance["pe_ratio"].source_id == SOURCE_YAHOO
    assert (
        result.snapshot.field_provenance["eps_trailing"].source_id == SOURCE_SEC_XBRL
    )
    assert result.snapshot.source_id == "merged"
    assert set(result.sources_used) == {SOURCE_YAHOO, SOURCE_SEC_XBRL}


def test_disagreement_prefers_sec_statements() -> None:
    yahoo = FinancialMetrics(
        ticker="AAPL",
        total_cash=10.0,
        balance_sheet=StatementSummary(total_assets=100.0),
        source_id=SOURCE_YAHOO,
    )
    sec = FinancialMetrics(
        ticker="AAPL",
        total_cash=50.0,
        balance_sheet=StatementSummary(total_assets=500.0),
        source_id=SOURCE_SEC_XBRL,
    )
    result = merge_fundamentals(
        [
            ProviderSnapshot(SOURCE_YAHOO, yahoo),
            ProviderSnapshot(SOURCE_SEC_XBRL, sec),
        ],
        ticker="AAPL",
    )
    assert result.snapshot.total_cash == 50.0
    assert result.snapshot.balance_sheet is not None
    assert result.snapshot.balance_sheet.total_assets == 500.0
    paths = {c.field_path for c in result.conflicts}
    assert "total_cash" in paths
    assert "balance_sheet.total_assets" in paths


def test_never_invents_values() -> None:
    yahoo = FinancialMetrics(ticker="AAPL", pe_ratio=25.0, source_id=SOURCE_YAHOO)
    result = merge_fundamentals(
        [ProviderSnapshot(SOURCE_YAHOO, yahoo)],
        ticker="AAPL",
    )
    assert result.snapshot.eps_trailing is None
    assert result.snapshot.balance_sheet is None
    assert result.conflicts == []


def test_empty_providers() -> None:
    result = merge_fundamentals([], ticker="AAPL")
    assert result.snapshot.ticker == "AAPL"
    assert result.sources_used == []


def test_list_fill_from_sec() -> None:
    yahoo = FinancialMetrics(ticker="AAPL", pe_ratio=1.0, source_id=SOURCE_YAHOO)
    sec = FinancialMetrics(
        ticker="AAPL",
        earnings_history=[PeriodMetric(period="2024", value=1.0)],
        source_id=SOURCE_SEC_XBRL,
    )
    result = merge_fundamentals(
        [
            ProviderSnapshot(SOURCE_YAHOO, yahoo),
            ProviderSnapshot(SOURCE_SEC_XBRL, sec),
        ],
        ticker="AAPL",
    )
    assert len(result.snapshot.earnings_history) == 1


def test_market_field_disagreement_prefers_yahoo() -> None:
    yahoo = FinancialMetrics(ticker="AAPL", pe_ratio=25.0, source_id=SOURCE_YAHOO)
    sec = FinancialMetrics(ticker="AAPL", pe_ratio=40.0, source_id=SOURCE_SEC_XBRL)
    result = merge_fundamentals(
        [
            ProviderSnapshot(SOURCE_YAHOO, yahoo),
            ProviderSnapshot(SOURCE_SEC_XBRL, sec),
        ],
        ticker="AAPL",
    )
    assert result.snapshot.pe_ratio == 25.0
    assert result.snapshot.field_provenance["pe_ratio"].source_id == SOURCE_YAHOO
    pe_conflicts = [c for c in result.conflicts if c.field_path == "pe_ratio"]
    assert len(pe_conflicts) == 1
    assert pe_conflicts[0].chosen_source_id == SOURCE_YAHOO


def test_float_within_tolerance_no_conflict() -> None:
    yahoo = FinancialMetrics(ticker="AAPL", total_cash=100.0, source_id=SOURCE_YAHOO)
    sec = FinancialMetrics(ticker="AAPL", total_cash=100.5, source_id=SOURCE_SEC_XBRL)
    result = merge_fundamentals(
        [
            ProviderSnapshot(SOURCE_YAHOO, yahoo),
            ProviderSnapshot(SOURCE_SEC_XBRL, sec),
        ],
        ticker="AAPL",
    )
    assert result.snapshot.total_cash == 100.5  # SEC wins statement field
    assert result.conflicts == []


def test_yahoo_profile_and_returns_preserved() -> None:
    yahoo = FinancialMetrics(
        ticker="AAPL",
        pe_ratio=25.0,
        profile=CompanyProfile(name="Apple Inc.", sector="Technology"),
        returns=PriceReturns(return_1y=0.2, return_ytd=0.1),
        source_id=SOURCE_YAHOO,
    )
    sec = FinancialMetrics(
        ticker="AAPL",
        eps_trailing=6.5,
        source_id=SOURCE_SEC_XBRL,
    )
    result = merge_fundamentals(
        [
            ProviderSnapshot(SOURCE_YAHOO, yahoo),
            ProviderSnapshot(SOURCE_SEC_XBRL, sec),
        ],
        ticker="AAPL",
    )
    assert result.snapshot.profile is not None
    assert result.snapshot.profile.name == "Apple Inc."
    assert result.snapshot.returns is not None
    assert result.snapshot.returns.return_1y == 0.2
    assert result.snapshot.field_provenance["profile"].source_id == SOURCE_YAHOO


def test_none_providers_filtered() -> None:
    yahoo = FinancialMetrics(ticker="AAPL", pe_ratio=12.0, source_id=SOURCE_YAHOO)
    result = merge_fundamentals(
        [None, ProviderSnapshot(SOURCE_YAHOO, yahoo), None],
        ticker="AAPL",
    )
    assert result.snapshot.pe_ratio == 12.0
    assert result.sources_used == [SOURCE_YAHOO]
    assert result.snapshot.source_id == SOURCE_YAHOO


def test_av_fills_forward_pe_when_yahoo_gaps() -> None:
    yahoo = FinancialMetrics(
        ticker="AAPL",
        pe_ratio=25.0,
        forward_pe=None,
        source_id=SOURCE_YAHOO,
    )
    av = FinancialMetrics(
        ticker="AAPL",
        forward_pe=22.0,
        pe_ratio=30.0,
        source_id=SOURCE_ALPHA_VANTAGE,
    )
    result = merge_fundamentals(
        [
            ProviderSnapshot(SOURCE_YAHOO, yahoo),
            ProviderSnapshot(SOURCE_ALPHA_VANTAGE, av),
        ],
        ticker="AAPL",
    )
    assert result.snapshot.forward_pe == 22.0
    assert result.snapshot.pe_ratio == 25.0  # Yahoo wins market disagreement
    assert (
        result.snapshot.field_provenance["forward_pe"].source_id
        == SOURCE_ALPHA_VANTAGE
    )
    assert result.snapshot.field_provenance["pe_ratio"].source_id == SOURCE_YAHOO

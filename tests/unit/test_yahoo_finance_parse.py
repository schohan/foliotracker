"""Yahoo Finance tool — unit tests with mocked yfinance."""

from __future__ import annotations

from concurrent.futures import TimeoutError as FuturesTimeout

import pytest

from app.schemas.financials import FinancialMetrics
from app.tools.finance import yahoo_finance
from app.tools.finance.yahoo_finance import (
    TickerNotFoundError,
    ToolParseError,
    ToolTimeoutError,
    ToolUpstreamError,
    fetch_financial_metrics,
    metrics_from_bundle,
    ticker_exists,
)


def _empty_enrichment() -> dict:
    return {
        "history_closes": [],
        "income_quarterly": {},
        "balance_quarterly": {},
        "cashflow_quarterly": {},
    }


def _ok_info() -> dict:
    return {
        "symbol": "AAPL",
        "shortName": "Apple Inc.",
        "longBusinessSummary": "Apple designs consumer electronics. " * 40,
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "marketCap": 3.5e12,
        "trailingPE": 28.0,
        "forwardPE": 25.0,
        "trailingEps": 6.4,
        "forwardEps": 7.1,
        "earningsGrowth": 0.12,
        "returnOnEquity": 1.4,
        "currentRatio": 1.0,
        "totalCash": 5.0e10,
        "totalDebt": 1.0e11,
        "revenueGrowth": 0.05,
        "grossMargins": 0.46,
        "operatingMargins": 0.30,
        "freeCashflow": 1.0e11,
        "debtToEquity": 150.0,
        "quoteType": "EQUITY",
        "regularMarketPrice": 190.0,
    }


def _ok_bundle() -> dict:
    return {
        "info": _ok_info(),
        "history_closes": [
            ("2025-07-25", 180.0),
            ("2025-10-25", 200.0),
            ("2026-01-02", 210.0),
            ("2026-07-25", 220.0),
        ],
        "income_quarterly": {
            "Total Revenue": {
                "2025-12-31": 1.0e11,
                "2026-03-31": 1.1e11,
                "2026-06-30": 1.2e11,
            },
            "Net Income": {
                "2025-12-31": 2.0e10,
                "2026-03-31": 2.2e10,
                "2026-06-30": 2.4e10,
            },
        },
        "balance_quarterly": {
            "Total Assets": {"2026-06-30": 3.5e11},
            "Total Liabilities Net Minority Interest": {"2026-06-30": 2.0e11},
            "Cash And Cash Equivalents": {"2026-06-30": 4.0e10},
            "Total Debt": {"2026-06-30": 9.0e10},
        },
        "cashflow_quarterly": {
            "Operating Cash Flow": {"2026-06-30": 3.0e10},
            "Free Cash Flow": {"2026-06-30": 2.5e10},
        },
    }


def test_yahoo_returns_financial_metrics_for_known_ticker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        yahoo_finance,
        "_fetch_yahoo_bundle",
        lambda ticker: {"info": _ok_info(), **_empty_enrichment()},
    )
    metrics = fetch_financial_metrics("AAPL")
    assert isinstance(metrics, FinancialMetrics)
    assert metrics.ticker == "AAPL"
    assert metrics.pe_ratio == 28.0
    assert metrics.trailing_pe == 28.0
    assert metrics.forward_pe == 25.0
    assert metrics.revenue_growth == 0.05
    assert metrics.debt_to_equity == pytest.approx(1.5)
    assert metrics.profile is not None
    assert metrics.profile.sector == "Technology"
    assert metrics.profile.summary is not None
    assert len(metrics.profile.summary) <= 500


def test_metrics_from_bundle_returns_and_statements() -> None:
    metrics = metrics_from_bundle("AAPL", _ok_bundle())
    assert metrics.returns is not None
    assert metrics.returns.return_1y == pytest.approx((220.0 / 180.0) - 1.0)
    # YTD target 2026-01-01 → last on/before is 2025-10-25 (200)
    assert metrics.returns.return_ytd == pytest.approx((220.0 / 200.0) - 1.0)
    # ~3m before 2026-07-25 ≈ 2026-04-23 → last on/before is 2026-01-02
    assert metrics.returns.return_3m == pytest.approx((220.0 / 210.0) - 1.0)
    assert len(metrics.revenue_history) == 3
    assert metrics.revenue_history[-1].value == 1.2e11
    assert metrics.balance_sheet is not None
    assert metrics.balance_sheet.total_assets == 3.5e11
    assert metrics.cash_flow is not None
    assert metrics.cash_flow.free_cash_flow == 2.5e10
    assert metrics.forward_pe == 25.0
    assert metrics.source_id == "yahoo"
    assert len(metrics.history_closes) >= 2
    assert metrics.history_closes[-1][1] == 220.0


def test_yahoo_timeout_raises_tool_timeout_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class BoomPool:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def submit(self, fn, *a, **k):
            class Fut:
                def result(self, timeout=None):
                    raise FuturesTimeout()

            return Fut()

    monkeypatch.setattr(yahoo_finance, "ThreadPoolExecutor", BoomPool)
    with pytest.raises(ToolTimeoutError):
        fetch_financial_metrics("AAPL", timeout_seconds=0.001)


def test_yahoo_unknown_ticker_raises_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        yahoo_finance,
        "_fetch_yahoo_bundle",
        lambda ticker: {"info": {}, **_empty_enrichment()},
    )
    with pytest.raises(TickerNotFoundError):
        fetch_financial_metrics("ZZZZ")


def test_ticker_exists_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(yahoo_finance, "_fetch_info", lambda _t: _ok_info())
    assert ticker_exists("AAPL") is True


def test_ticker_exists_false_empty_info(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(yahoo_finance, "_fetch_info", lambda _t: {})
    assert ticker_exists("ZZZZ") is False


def test_ticker_exists_unknown_on_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    class BoomPool:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def submit(self, fn, *a, **k):
            class F:
                def result(self, timeout=None):
                    raise FuturesTimeout()

            return F()

    monkeypatch.setattr(yahoo_finance, "ThreadPoolExecutor", BoomPool)
    assert ticker_exists("AAPL", timeout_seconds=0.001) is None


def test_yahoo_malformed_payload_raises_parse_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def bad(_ticker: str):
        raise ToolParseError("yfinance info was not a dict")

    monkeypatch.setattr(yahoo_finance, "_fetch_yahoo_bundle", bad)
    with pytest.raises(ToolParseError):
        fetch_financial_metrics("AAPL")


def test_yahoo_upstream_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def bad(_ticker: str):
        raise RuntimeError("network down")

    monkeypatch.setattr(yahoo_finance, "_fetch_yahoo_bundle", bad)
    with pytest.raises(ToolUpstreamError):
        fetch_financial_metrics("AAPL")

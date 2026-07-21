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
)


def _ok_info() -> dict:
    return {
        "symbol": "AAPL",
        "shortName": "Apple Inc.",
        "marketCap": 3.5e12,
        "trailingPE": 28.0,
        "revenueGrowth": 0.05,
        "grossMargins": 0.46,
        "operatingMargins": 0.30,
        "freeCashflow": 1.0e11,
        "debtToEquity": 150.0,
        "quoteType": "EQUITY",
        "regularMarketPrice": 190.0,
    }


def test_yahoo_returns_financial_metrics_for_known_ticker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(yahoo_finance, "_fetch_info", lambda ticker: _ok_info())
    metrics = fetch_financial_metrics("AAPL")
    assert isinstance(metrics, FinancialMetrics)
    assert metrics.ticker == "AAPL"
    assert metrics.pe_ratio == 28.0
    assert metrics.revenue_growth == 0.05
    assert metrics.debt_to_equity == pytest.approx(1.5)


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
    monkeypatch.setattr(yahoo_finance, "_fetch_info", lambda ticker: {})
    with pytest.raises(TickerNotFoundError):
        fetch_financial_metrics("ZZZZ")


def test_yahoo_malformed_payload_raises_parse_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def bad(_ticker: str):
        raise ToolParseError("yfinance info was not a dict")

    monkeypatch.setattr(yahoo_finance, "_fetch_info", bad)
    with pytest.raises(ToolParseError):
        fetch_financial_metrics("AAPL")


def test_yahoo_upstream_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def bad(_ticker: str):
        raise RuntimeError("network down")

    monkeypatch.setattr(yahoo_finance, "_fetch_info", bad)
    with pytest.raises(ToolUpstreamError):
        fetch_financial_metrics("AAPL")

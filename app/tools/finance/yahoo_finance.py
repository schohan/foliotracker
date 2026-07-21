"""Yahoo Finance market data tool via yfinance.

Fetches structured FinancialMetrics. Agents must not call HTTP themselves.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from typing import Any

import yfinance as yf

from app.configs.settings import settings
from app.schemas.financials import FinancialMetrics
from app.schemas.ticker import normalize_ticker

logger = logging.getLogger(__name__)


class ToolTimeoutError(TimeoutError):
    """Yahoo request exceeded YAHOO_TIMEOUT_SECONDS."""


class ToolUpstreamError(RuntimeError):
    """Yahoo / yfinance upstream failure."""


class TickerNotFoundError(LookupError):
    """Ticker not found in Yahoo Finance."""


class ToolParseError(ValueError):
    """Yahoo payload could not be parsed into FinancialMetrics."""


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _metrics_from_info(ticker: str, info: dict[str, Any]) -> FinancialMetrics:
    debt = _as_float(info.get("debtToEquity"))
    if debt is not None and debt > 5:
        # yfinance reports D/E scaled like 79.5 meaning 0.795
        debt = debt / 100.0

    return FinancialMetrics(
        ticker=ticker,
        market_cap=_as_float(info.get("marketCap")),
        revenue_growth=_as_float(info.get("revenueGrowth")),
        gross_margin=_as_float(info.get("grossMargins")),
        operating_margin=_as_float(info.get("operatingMargins")),
        free_cash_flow=_as_float(info.get("freeCashflow")),
        debt_to_equity=debt,
        pe_ratio=_as_float(info.get("trailingPE") or info.get("forwardPE")),
    )


def _fetch_info(ticker: str) -> dict[str, Any]:
    stock = yf.Ticker(ticker)
    info = stock.info or {}
    if not isinstance(info, dict):
        raise ToolParseError("yfinance info was not a dict")
    return info


def fetch_financial_metrics(
    ticker: str,
    *,
    timeout_seconds: float | None = None,
) -> FinancialMetrics:
    """Fetch FinancialMetrics for a ticker from Yahoo Finance (yfinance).

    Args:
        ticker: Equity symbol (validated/normalized).
        timeout_seconds: Override default YAHOO_TIMEOUT_SECONDS.

    Raises:
        InvalidTickerError, ToolTimeoutError, ToolUpstreamError,
        TickerNotFoundError, ToolParseError
    """
    normalized = normalize_ticker(ticker)
    timeout = (
        float(timeout_seconds)
        if timeout_seconds is not None
        else float(settings.yahoo_timeout_seconds)
    )

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_fetch_info, normalized)
            info = future.result(timeout=timeout)
    except FuturesTimeout as exc:
        logger.warning("yahoo_timeout ticker=%s", normalized)
        raise ToolTimeoutError(f"Yahoo timeout after {timeout}s for {normalized}") from exc
    except TickerNotFoundError:
        raise
    except ToolParseError:
        raise
    except Exception as exc:  # noqa: BLE001 — wrap unknown yfinance failures
        logger.warning("yahoo_upstream ticker=%s err=%s", normalized, exc)
        raise ToolUpstreamError(f"Yahoo upstream error for {normalized}: {exc}") from exc

    # Explicit not-found heuristics
    quote_type = info.get("quoteType")
    if info.get("trailingPegRatio") is None and info.get("marketCap") is None and info.get("regularMarketPrice") is None:
        if not info.get("shortName") and not info.get("longName"):
            raise TickerNotFoundError(f"ticker not found: {normalized}")

    metrics = _metrics_from_info(normalized, info)
    if (
        metrics.market_cap is None
        and metrics.pe_ratio is None
        and metrics.revenue_growth is None
        and metrics.gross_margin is None
        and metrics.operating_margin is None
        and metrics.free_cash_flow is None
        and metrics.debt_to_equity is None
    ):
        raise TickerNotFoundError(f"ticker not found: {normalized}")

    logger.info("yahoo_ok ticker=%s quoteType=%s", normalized, quote_type)
    return metrics


def run(ticker: str, **kwargs: Any) -> FinancialMetrics:
    """Scaffold-compatible entrypoint."""
    return fetch_financial_metrics(ticker, **kwargs)

"""Alpha Vantage OVERVIEW → forward / market fill-gaps (Phase 2C).

Fetches ``function=OVERVIEW`` and maps forward P/E plus related market
fields into ``FinancialMetrics``. Soft-fail provider: agents must not
call HTTP themselves. Requires ``ALPHA_VANTAGE_API_KEY``.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.configs.settings import settings
from app.schemas.financials import CompanyProfile, FinancialMetrics
from app.schemas.ticker import normalize_ticker

logger = logging.getLogger(__name__)

OVERVIEW_URL = "https://www.alphavantage.co/query"


class ToolTimeoutError(TimeoutError):
    """Alpha Vantage request exceeded timeout."""


class ToolUpstreamError(RuntimeError):
    """Alpha Vantage upstream / rate-limit / API note failure."""


class ToolParseError(ValueError):
    """Alpha Vantage payload could not be parsed."""


class MissingApiKeyError(RuntimeError):
    """ALPHA_VANTAGE_API_KEY is not configured."""


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    if isinstance(value, str) and value.strip() in {"-", "None", "null", "N/A"}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_div(num: float | None, den: float | None) -> float | None:
    if num is None or den is None or den == 0:
        return None
    return num / den


def _http_get_json(url: str, *, timeout: float) -> dict[str, Any]:
    req = Request(
        url,
        headers={
            "User-Agent": "FolioTracker/0.1 (alpha_vantage)",
            "Accept": "application/json",
        },
    )
    with urlopen(req, timeout=timeout) as resp:  # noqa: S310 — fixed AV host
        raw = resp.read()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ToolParseError("invalid Alpha Vantage JSON") from exc
    if not isinstance(payload, dict):
        raise ToolParseError("Alpha Vantage JSON is not an object")
    return payload


def parse_overview_json(
    payload: dict[str, Any],
    *,
    ticker: str,
) -> FinancialMetrics:
    """Map OVERVIEW JSON into FinancialMetrics (pure, testable).

    Primary fill-gap fields: forward/trailing P/E, valuation multiples
    (PEG, P/S, P/B, EV ratios), profit margin, ROA/ROE, revenue TTM.
    ``eps_forward`` and ``enterprise_value`` are not on OVERVIEW (left null).
    """
    if not isinstance(payload, dict):
        raise ToolParseError(f"OVERVIEW payload is not an object for {ticker}")

    for ban_key in ("Note", "Information", "Error Message"):
        msg = payload.get(ban_key)
        if isinstance(msg, str) and msg.strip():
            raise ToolUpstreamError(f"Alpha Vantage {ban_key}: {msg.strip()[:200]}")

    symbol = payload.get("Symbol")
    if not symbol and not payload.get("Name") and not payload.get("ForwardPE"):
        raise ToolParseError(f"empty OVERVIEW for {ticker}")

    revenue = _as_float(payload.get("RevenueTTM"))
    gross_profit = _as_float(payload.get("GrossProfitTTM"))
    name = payload.get("Name")
    sector = payload.get("Sector")
    industry = payload.get("Industry")
    description = payload.get("Description")
    profile = None
    if any(
        isinstance(v, str) and v.strip()
        for v in (name, sector, industry, description)
    ):
        summary = None
        if isinstance(description, str) and description.strip():
            summary = description.strip()
            if len(summary) > 500:
                summary = summary[:499].rstrip() + "…"
        profile = CompanyProfile(
            name=name.strip() if isinstance(name, str) and name.strip() else None,
            sector=sector.strip() if isinstance(sector, str) and sector.strip() else None,
            industry=(
                industry.strip()
                if isinstance(industry, str) and industry.strip()
                else None
            ),
            summary=summary,
        )

    metrics = FinancialMetrics(
        ticker=ticker,
        market_cap=_as_float(payload.get("MarketCapitalization")),
        revenue_growth=_as_float(payload.get("QuarterlyRevenueGrowthYOY")),
        gross_margin=_safe_div(gross_profit, revenue),
        operating_margin=_as_float(payload.get("OperatingMarginTTM")),
        return_on_equity=_as_float(payload.get("ReturnOnEquityTTM")),
        pe_ratio=_as_float(payload.get("PERatio")),
        trailing_pe=_as_float(payload.get("TrailingPE")),
        forward_pe=_as_float(payload.get("ForwardPE")),
        eps_trailing=_as_float(payload.get("EPS") or payload.get("DilutedEPSTTM")),
        eps_forward=None,  # not on OVERVIEW; Yahoo / future estimate endpoint
        earnings_growth=_as_float(payload.get("QuarterlyEarningsGrowthYOY")),
        peg_ratio=_as_float(payload.get("PEGRatio")),
        price_to_sales=_as_float(payload.get("PriceToSalesRatioTTM")),
        price_to_book=_as_float(payload.get("PriceToBookRatio")),
        ev_to_revenue=_as_float(payload.get("EVToRevenue")),
        ev_to_ebitda=_as_float(payload.get("EVToEBITDA")),
        profit_margin=_as_float(payload.get("ProfitMargin")),
        return_on_assets=_as_float(payload.get("ReturnOnAssetsTTM")),
        revenue_ttm=revenue,
        profile=profile,
        source_id="alpha_vantage",
        as_of=datetime.now(timezone.utc),
    )

    if (
        metrics.forward_pe is None
        and metrics.pe_ratio is None
        and metrics.trailing_pe is None
        and metrics.eps_trailing is None
        and metrics.market_cap is None
    ):
        raise ToolParseError(f"no usable OVERVIEW market fields for {ticker}")

    return metrics


def fetch_alpha_vantage_fundamentals(
    ticker: str,
    *,
    timeout_seconds: float | None = None,
    api_key: str | None = None,
) -> FinancialMetrics:
    """Fetch Alpha Vantage OVERVIEW and map to FinancialMetrics.

    Raises:
        MissingApiKeyError, ToolTimeoutError, ToolUpstreamError, ToolParseError
    """
    normalized = normalize_ticker(ticker)
    key = (api_key if api_key is not None else settings.alpha_vantage_api_key) or ""
    key = key.strip()
    if not key:
        raise MissingApiKeyError("ALPHA_VANTAGE_API_KEY is not set")

    timeout = (
        float(timeout_seconds)
        if timeout_seconds is not None
        else float(settings.alpha_vantage_timeout_seconds)
    )

    def _work() -> FinancialMetrics:
        params = urlencode(
            {
                "function": "OVERVIEW",
                "symbol": normalized,
                "apikey": key,
            }
        )
        url = f"{OVERVIEW_URL}?{params}"
        payload = _http_get_json(url, timeout=timeout)
        return parse_overview_json(payload, ticker=normalized)

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_work)
            metrics = future.result(timeout=timeout)
    except FuturesTimeout as exc:
        logger.warning("alpha_vantage_timeout ticker=%s", normalized)
        raise ToolTimeoutError(
            f"Alpha Vantage timeout after {timeout}s for {normalized}"
        ) from exc
    except (MissingApiKeyError, ToolParseError, ToolUpstreamError, ToolTimeoutError):
        raise
    except HTTPError as exc:
        logger.warning("alpha_vantage_upstream ticker=%s err=%s", normalized, exc)
        raise ToolUpstreamError(
            f"Alpha Vantage HTTP error for {normalized}: {exc.code}"
        ) from exc
    except URLError as exc:
        logger.warning("alpha_vantage_upstream ticker=%s err=%s", normalized, exc)
        raise ToolUpstreamError(
            f"Alpha Vantage upstream error for {normalized}: {exc.reason}"
        ) from exc
    except Exception as exc:  # noqa: BLE001
        if isinstance(
            exc,
            (ToolTimeoutError, ToolUpstreamError, ToolParseError, MissingApiKeyError),
        ):
            raise
        logger.warning("alpha_vantage_upstream ticker=%s err=%s", normalized, exc)
        raise ToolUpstreamError(
            f"Alpha Vantage upstream error for {normalized}: {exc}"
        ) from exc

    logger.info(
        "alpha_vantage_ok ticker=%s forward_pe=%s pe=%s",
        normalized,
        metrics.forward_pe,
        metrics.pe_ratio,
    )
    return metrics


def run(ticker: str, **kwargs: Any) -> FinancialMetrics:
    """Scaffold-compatible entrypoint."""
    return fetch_alpha_vantage_fundamentals(ticker, **kwargs)

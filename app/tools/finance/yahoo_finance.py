"""Yahoo Finance market data tool via yfinance.

Fetches enriched FinancialMetrics (Phase 2C.2). Agents must not call HTTP themselves.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from datetime import datetime, timezone
from typing import Any

import yfinance as yf

from app.configs.settings import settings
from app.schemas.financials import (
    CompanyProfile,
    FinancialMetrics,
    PeriodMetric,
    PriceReturns,
    StatementSummary,
)
from app.schemas.ticker import normalize_ticker

logger = logging.getLogger(__name__)

_SUMMARY_MAX_CHARS = 500
_HISTORY_MAX_PERIODS = 8


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
        # pandas / numpy scalars
        if hasattr(value, "item"):
            value = value.item()
        return float(value)
    except (TypeError, ValueError):
        return None


def _truncate(text: str | None, limit: int = _SUMMARY_MAX_CHARS) -> str | None:
    if not text or not isinstance(text, str):
        return None
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _df_to_nested(df: Any) -> dict[str, dict[str, float | None]]:
    """Convert a yfinance statement DataFrame to {row: {period: value}}."""
    if df is None:
        return {}
    try:
        empty = getattr(df, "empty", True)
        if empty:
            return {}
    except Exception:  # noqa: BLE001
        return {}

    out: dict[str, dict[str, float | None]] = {}
    try:
        for row_label, row in df.iterrows():
            key = str(row_label)
            periods: dict[str, float | None] = {}
            for col, val in row.items():
                period = str(col)[:10] if col is not None else "unknown"
                periods[period] = _as_float(val)
            out[key] = periods
    except Exception:  # noqa: BLE001
        return {}
    return out


def _latest_period(periods: dict[str, float | None]) -> str | None:
    if not periods:
        return None
    return sorted(periods.keys(), reverse=True)[0]


def _lookup_row(
    nested: dict[str, dict[str, float | None]],
    *candidates: str,
) -> dict[str, float | None]:
    lower_map = {k.lower(): k for k in nested}
    for name in candidates:
        key = lower_map.get(name.lower())
        if key is not None:
            return nested[key]
    # fuzzy contains
    for name in candidates:
        needle = name.lower()
        for k_lower, original in lower_map.items():
            if needle in k_lower:
                return nested[original]
    return {}


def _history_series(
    nested_row: dict[str, float | None],
    *,
    max_periods: int = _HISTORY_MAX_PERIODS,
) -> list[PeriodMetric]:
    periods = sorted(nested_row.keys(), reverse=True)[:max_periods]
    # chronological for consumers
    periods = list(reversed(periods))
    return [PeriodMetric(period=p, value=nested_row.get(p)) for p in periods]


def _returns_from_closes(closes: list[tuple[str, float]]) -> PriceReturns | None:
    """Compute 3M / 1Y / YTD returns from (date_iso, close) ascending series."""
    if len(closes) < 2:
        return None
    try:
        last_date = datetime.fromisoformat(closes[-1][0]).date()
        last_px = closes[-1][1]
    except (TypeError, ValueError):
        return None
    if last_px <= 0:
        return None

    def _return_since(target_date) -> float | None:
        # Prefer last close on/before target; else first close after.
        before = None
        after = None
        for d_str, px in closes:
            try:
                d = datetime.fromisoformat(d_str).date()
            except (TypeError, ValueError):
                continue
            if d <= target_date:
                before = px
            elif after is None:
                after = px
        chosen = before if before is not None else after
        if chosen is None or chosen <= 0:
            return None
        return (last_px / chosen) - 1.0

    from datetime import timedelta

    r3 = _return_since(last_date - timedelta(days=93))
    r1 = _return_since(last_date - timedelta(days=365))
    ytd = _return_since(last_date.replace(month=1, day=1))
    if r3 is None and r1 is None and ytd is None:
        return None
    return PriceReturns(return_3m=r3, return_1y=r1, return_ytd=ytd)


def _statement_summary(
    income: dict[str, dict[str, float | None]],
    balance: dict[str, dict[str, float | None]],
    cashflow: dict[str, dict[str, float | None]],
) -> tuple[StatementSummary | None, StatementSummary | None]:
    rev_row = _lookup_row(income, "Total Revenue", "Operating Revenue")
    ni_row = _lookup_row(income, "Net Income", "Net Income Common Stockholders")
    assets_row = _lookup_row(balance, "Total Assets")
    liab_row = _lookup_row(
        balance,
        "Total Liabilities Net Minority Interest",
        "Total Liabilities",
    )
    cash_row = _lookup_row(
        balance,
        "Cash And Cash Equivalents",
        "Cash Cash Equivalents And Short Term Investments",
    )
    debt_row = _lookup_row(balance, "Total Debt", "Long Term Debt")
    ocf_row = _lookup_row(
        cashflow,
        "Operating Cash Flow",
        "Cash Flow From Continuing Operating Activities",
    )
    fcf_row = _lookup_row(cashflow, "Free Cash Flow")

    income_as_of = _latest_period(rev_row) or _latest_period(ni_row)
    bal_as_of = _latest_period(assets_row) or _latest_period(liab_row)
    cf_as_of = _latest_period(ocf_row) or _latest_period(fcf_row)

    balance_sheet = None
    if bal_as_of is not None:
        balance_sheet = StatementSummary(
            as_of=bal_as_of,
            total_assets=assets_row.get(bal_as_of) if assets_row else None,
            total_liabilities=liab_row.get(bal_as_of) if liab_row else None,
            total_cash=cash_row.get(bal_as_of) if cash_row else None,
            total_debt=debt_row.get(bal_as_of) if debt_row else None,
        )

    cash_flow = None
    if income_as_of is not None or cf_as_of is not None:
        period = income_as_of or cf_as_of
        cash_flow = StatementSummary(
            as_of=period,
            total_revenue=rev_row.get(income_as_of) if income_as_of else None,
            net_income=ni_row.get(income_as_of) if income_as_of else None,
            operating_cashflow=ocf_row.get(cf_as_of) if cf_as_of else None,
            free_cash_flow=fcf_row.get(cf_as_of) if cf_as_of else None,
        )

    return balance_sheet, cash_flow


def metrics_from_bundle(ticker: str, bundle: dict[str, Any]) -> FinancialMetrics:
    """Pure parse: Yahoo raw bundle → FinancialMetrics (unit-testable)."""
    info = bundle.get("info") or {}
    if not isinstance(info, dict):
        raise ToolParseError("yfinance info was not a dict")

    trailing = _as_float(info.get("trailingPE"))
    forward = _as_float(info.get("forwardPE"))
    pe = trailing if trailing is not None else forward

    debt = _as_float(info.get("debtToEquity"))
    if debt is not None and debt > 5:
        # yfinance reports D/E scaled like 79.5 meaning 0.795
        debt = debt / 100.0

    name = info.get("shortName") or info.get("longName")
    summary = _truncate(info.get("longBusinessSummary"))
    profile = None
    if name or info.get("sector") or info.get("industry") or summary:
        profile = CompanyProfile(
            name=str(name) if name else None,
            sector=str(info["sector"]) if info.get("sector") else None,
            industry=str(info["industry"]) if info.get("industry") else None,
            summary=summary,
        )

    closes = bundle.get("history_closes") or []
    typed: list[tuple[str, float]] = []
    returns = None
    if isinstance(closes, list) and closes:
        for item in closes:
            if (
                isinstance(item, (list, tuple))
                and len(item) == 2
                and item[1] is not None
            ):
                typed.append((str(item[0])[:10], float(item[1])))
        returns = _returns_from_closes(typed)

    income = bundle.get("income_quarterly") or {}
    balance = bundle.get("balance_quarterly") or {}
    cashflow = bundle.get("cashflow_quarterly") or {}
    if not isinstance(income, dict):
        income = {}
    if not isinstance(balance, dict):
        balance = {}
    if not isinstance(cashflow, dict):
        cashflow = {}

    rev_row = _lookup_row(income, "Total Revenue", "Operating Revenue")
    ni_row = _lookup_row(income, "Net Income", "Net Income Common Stockholders")
    revenue_history = _history_series(rev_row) if rev_row else []
    earnings_history = _history_series(ni_row) if ni_row else []
    balance_sheet, cash_flow = _statement_summary(income, balance, cashflow)

    fcf = _as_float(info.get("freeCashflow"))
    if fcf is None and cash_flow is not None:
        fcf = cash_flow.free_cash_flow

    total_cash = _as_float(info.get("totalCash"))
    if total_cash is None and balance_sheet is not None:
        total_cash = balance_sheet.total_cash
    total_debt = _as_float(info.get("totalDebt"))
    if total_debt is None and balance_sheet is not None:
        total_debt = balance_sheet.total_debt

    return FinancialMetrics(
        ticker=ticker,
        market_cap=_as_float(info.get("marketCap")),
        revenue_growth=_as_float(info.get("revenueGrowth")),
        gross_margin=_as_float(info.get("grossMargins")),
        operating_margin=_as_float(info.get("operatingMargins")),
        free_cash_flow=fcf,
        debt_to_equity=debt,
        pe_ratio=pe,
        trailing_pe=trailing,
        forward_pe=forward,
        eps_trailing=_as_float(info.get("trailingEps")),
        eps_forward=_as_float(info.get("forwardEps")),
        earnings_growth=_as_float(info.get("earningsGrowth")),
        return_on_equity=_as_float(info.get("returnOnEquity")),
        current_ratio=_as_float(info.get("currentRatio")),
        total_cash=total_cash,
        total_debt=total_debt,
        profile=profile,
        returns=returns,
        revenue_history=revenue_history,
        earnings_history=earnings_history,
        balance_sheet=balance_sheet,
        cash_flow=cash_flow,
        history_closes=typed,
        source_id="yahoo",
        as_of=datetime.now(timezone.utc),
    )


def _fetch_info(ticker: str) -> dict[str, Any]:
    """Fetch Yahoo ``info`` dict (patch point for unit tests)."""
    stock = yf.Ticker(ticker)
    info = stock.info or {}
    if not isinstance(info, dict):
        raise ToolParseError("yfinance info was not a dict")
    return info


def ticker_exists(
    ticker: str,
    *,
    timeout_seconds: float | None = None,
) -> bool | None:
    """Lightweight quote existence check (info only — no statements).

    Returns:
        True if Yahoo returns a recognizable quote,
        False if Yahoo clearly has no such symbol,
        None on timeout / upstream failure (unknown — caller may fail open).
    """
    normalized = normalize_ticker(ticker)
    timeout = (
        float(timeout_seconds)
        if timeout_seconds is not None
        else min(float(settings.yahoo_timeout_seconds), 8.0)
    )
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_fetch_info, normalized)
            info = future.result(timeout=timeout)
    except FuturesTimeout:
        logger.warning("yahoo_exists_timeout ticker=%s", normalized)
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("yahoo_exists_upstream ticker=%s err=%s", normalized, exc)
        return None

    if not info:
        return False
    if (
        info.get("regularMarketPrice") is None
        and info.get("currentPrice") is None
        and info.get("marketCap") is None
        and info.get("trailingPegRatio") is None
        and not info.get("shortName")
        and not info.get("longName")
    ):
        return False
    quote_type = info.get("quoteType")
    if quote_type in ("NONE", "OTHER") and info.get("regularMarketPrice") is None:
        return False
    # Yahoo sometimes echoes the symbol with empty fundamentals for junk.
    if (
        info.get("regularMarketPrice") is None
        and info.get("currentPrice") is None
        and info.get("marketCap") is None
        and not info.get("exchange")
        and not info.get("quoteType")
    ):
        return False
    return True


def _fetch_yahoo_bundle(ticker: str) -> dict[str, Any]:
    """Live yfinance pull → JSON-safe bundle for parse + source cache."""
    info = _fetch_info(ticker)
    stock = yf.Ticker(ticker)

    history_closes: list[tuple[str, float]] = []
    try:
        hist = stock.history(period="1y")
        if hist is not None and not getattr(hist, "empty", True):
            series = hist["Close"]
            for idx, val in series.items():
                px = _as_float(val)
                if px is None:
                    continue
                if hasattr(idx, "date"):
                    d = idx.date().isoformat()
                else:
                    d = str(idx)[:10]
                history_closes.append((d, px))
    except Exception as exc:  # noqa: BLE001 — optional enrichment
        logger.info("yahoo_history_skip ticker=%s err=%s", ticker, exc)

    income: dict[str, dict[str, float | None]] = {}
    balance: dict[str, dict[str, float | None]] = {}
    cashflow: dict[str, dict[str, float | None]] = {}
    try:
        income = _df_to_nested(getattr(stock, "quarterly_income_stmt", None))
    except Exception as exc:  # noqa: BLE001
        logger.info("yahoo_income_skip ticker=%s err=%s", ticker, exc)
    try:
        balance = _df_to_nested(getattr(stock, "quarterly_balance_sheet", None))
    except Exception as exc:  # noqa: BLE001
        logger.info("yahoo_balance_skip ticker=%s err=%s", ticker, exc)
    try:
        cashflow = _df_to_nested(getattr(stock, "quarterly_cashflow", None))
    except Exception as exc:  # noqa: BLE001
        logger.info("yahoo_cashflow_skip ticker=%s err=%s", ticker, exc)

    return {
        "info": info,
        "history_closes": history_closes,
        "income_quarterly": income,
        "balance_quarterly": balance,
        "cashflow_quarterly": cashflow,
    }


def _metrics_from_info(ticker: str, info: dict[str, Any]) -> FinancialMetrics:
    return metrics_from_bundle(ticker, {"info": info})


def fetch_financial_metrics(
    ticker: str,
    *,
    timeout_seconds: float | None = None,
) -> FinancialMetrics:
    """Fetch enriched FinancialMetrics for a ticker from Yahoo Finance.

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
            future = pool.submit(_fetch_yahoo_bundle, normalized)
            bundle = future.result(timeout=timeout)
    except FuturesTimeout as exc:
        logger.warning("yahoo_timeout ticker=%s", normalized)
        raise ToolTimeoutError(
            f"Yahoo timeout after {timeout}s for {normalized}"
        ) from exc
    except TickerNotFoundError:
        raise
    except ToolParseError:
        raise
    except Exception as exc:  # noqa: BLE001 — wrap unknown yfinance failures
        logger.warning("yahoo_upstream ticker=%s err=%s", normalized, exc)
        raise ToolUpstreamError(
            f"Yahoo upstream error for {normalized}: {exc}"
        ) from exc

    info = bundle.get("info") or {}
    quote_type = info.get("quoteType") if isinstance(info, dict) else None
    if isinstance(info, dict):
        if (
            info.get("trailingPegRatio") is None
            and info.get("marketCap") is None
            and info.get("regularMarketPrice") is None
        ):
            if not info.get("shortName") and not info.get("longName"):
                raise TickerNotFoundError(f"ticker not found: {normalized}")

    metrics = metrics_from_bundle(normalized, bundle)
    core_empty = (
        metrics.market_cap is None
        and metrics.pe_ratio is None
        and metrics.trailing_pe is None
        and metrics.forward_pe is None
        and metrics.revenue_growth is None
        and metrics.gross_margin is None
        and metrics.operating_margin is None
        and metrics.free_cash_flow is None
        and metrics.debt_to_equity is None
        and not metrics.revenue_history
        and metrics.balance_sheet is None
    )
    if core_empty:
        raise TickerNotFoundError(f"ticker not found: {normalized}")

    logger.info(
        "yahoo_ok ticker=%s quoteType=%s forward_pe=%s returns=%s rev_periods=%s",
        normalized,
        quote_type,
        metrics.forward_pe,
        metrics.returns is not None,
        len(metrics.revenue_history),
    )
    return metrics


def run(ticker: str, **kwargs: Any) -> FinancialMetrics:
    """Scaffold-compatible entrypoint."""
    return fetch_financial_metrics(ticker, **kwargs)

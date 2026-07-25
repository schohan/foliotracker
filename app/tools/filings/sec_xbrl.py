"""SEC XBRL companyfacts → FundamentalsSnapshot (Phase 2C.3).

Fetches data.sec.gov companyfacts JSON and maps US-GAAP tags into
``FinancialMetrics``. No LLM. Agents must not call HTTP themselves.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.configs.settings import settings
from app.schemas.financials import (
    FinancialMetrics,
    PeriodMetric,
    StatementSummary,
)
from app.schemas.ticker import normalize_ticker
from app.tools.filings.sec_edgar import (
    TickerNotFoundError,
    ToolParseError,
    ToolTimeoutError,
    ToolUpstreamError,
    resolve_ticker_cik,
)

logger = logging.getLogger(__name__)

COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

# Prefer first matching US-GAAP concept that has usable USD facts.
_REVENUE_TAGS = (
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
)
_NET_INCOME_TAGS = ("NetIncomeLoss", "ProfitLoss")
_ASSETS_TAGS = ("Assets",)
_LIABILITIES_TAGS = ("Liabilities",)
_CASH_TAGS = (
    "CashAndCashEquivalentsAtCarryingValue",
    "CashCashEquivalentsAndShortTermInvestments",
    "Cash",
)
_DEBT_TAGS = (
    "LongTermDebt",
    "LongTermDebtNoncurrent",
    "LongTermDebtAndCapitalLeaseObligations",
    "DebtCurrent",
)
_GROSS_PROFIT_TAGS = ("GrossProfit",)
_OPERATING_INCOME_TAGS = ("OperatingIncomeLoss",)
_OCF_TAGS = ("NetCashProvidedByUsedInOperatingActivities",)
_CAPEX_TAGS = (
    "PaymentsToAcquirePropertyPlantAndEquipment",
    "PurchaseOfPropertyPlantAndEquipment",
)
_EPS_TAGS = ("EarningsPerShareDiluted", "EarningsPerShareBasic")
_EQUITY_TAGS = ("StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest")

_FORM_PRIORITY = ("10-K", "10-K/A", "10-Q", "10-Q/A")


def _http_get_bytes(url: str, *, timeout: float, user_agent: str) -> bytes:
    req = Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/json",
            "Accept-Encoding": "identity",
        },
    )
    with urlopen(req, timeout=timeout) as resp:  # noqa: S310 — fixed SEC hosts
        return resp.read()


def _usd_facts(concept: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not concept or not isinstance(concept, dict):
        return []
    units = concept.get("units") or {}
    if not isinstance(units, dict):
        return []
    rows = units.get("USD") or units.get("USD/shares") or []
    if not isinstance(rows, list):
        return []
    return [r for r in rows if isinstance(r, dict) and r.get("val") is not None]


def _pick_latest(
    facts: list[dict[str, Any]],
    *,
    prefer_instant: bool | None = None,
) -> dict[str, Any] | None:
    """Pick newest filed fact; prefer FY/10-K when dates tie."""

    def _key(row: dict[str, Any]) -> tuple:
        end = str(row.get("end") or "")
        filed = str(row.get("filed") or "")
        form = str(row.get("form") or "")
        form_rank = _FORM_PRIORITY.index(form) if form in _FORM_PRIORITY else 99
        has_start = 1 if row.get("start") else 0
        # prefer_instant True → prefer no start (balance sheet)
        # prefer_instant False → prefer duration (income/CF)
        instant_rank = 0
        if prefer_instant is True:
            instant_rank = 0 if not row.get("start") else 1
        elif prefer_instant is False:
            instant_rank = 0 if row.get("start") else 1
        return (end, filed, -form_rank, instant_rank, has_start)

    if not facts:
        return None
    return max(facts, key=_key)


def _first_concept_facts(
    us_gaap: dict[str, Any],
    tags: tuple[str, ...],
) -> list[dict[str, Any]]:
    for tag in tags:
        concept = us_gaap.get(tag)
        facts = _usd_facts(concept if isinstance(concept, dict) else None)
        if facts:
            return facts
    return []


def _history(
    facts: list[dict[str, Any]],
    *,
    limit: int = 8,
) -> list[PeriodMetric]:
    # Prefer quarterly/annual duration facts; newest first, unique ends.
    scored: list[tuple[str, float]] = []
    seen: set[str] = set()
    for row in sorted(
        facts,
        key=lambda r: (str(r.get("end") or ""), str(r.get("filed") or "")),
        reverse=True,
    ):
        end = str(row.get("end") or "")
        if not end or end in seen:
            continue
        # Prefer duration facts for history series
        if not row.get("start") and row.get("fp") not in ("FY", "Q1", "Q2", "Q3", "Q4"):
            continue
        seen.add(end)
        try:
            scored.append((end, float(row["val"])))
        except (TypeError, ValueError, KeyError):
            continue
        if len(scored) >= limit:
            break
    return [PeriodMetric(period=p, value=v) for p, v in scored]


def _safe_div(num: float | None, den: float | None) -> float | None:
    if num is None or den is None or den == 0:
        return None
    return num / den


def parse_companyfacts_json(
    payload: dict[str, Any],
    *,
    ticker: str,
) -> FinancialMetrics:
    """Map companyfacts JSON into FinancialMetrics (pure, testable)."""
    if not isinstance(payload, dict):
        raise ToolParseError(f"companyfacts JSON is not an object for {ticker}")

    facts_root = payload.get("facts") or {}
    if not isinstance(facts_root, dict):
        raise ToolParseError(f"missing facts for {ticker}")
    us_gaap = facts_root.get("us-gaap") or {}
    if not isinstance(us_gaap, dict):
        us_gaap = {}

    rev_facts = _first_concept_facts(us_gaap, _REVENUE_TAGS)
    ni_facts = _first_concept_facts(us_gaap, _NET_INCOME_TAGS)
    assets_facts = _first_concept_facts(us_gaap, _ASSETS_TAGS)
    liab_facts = _first_concept_facts(us_gaap, _LIABILITIES_TAGS)
    cash_facts = _first_concept_facts(us_gaap, _CASH_TAGS)
    debt_facts = _first_concept_facts(us_gaap, _DEBT_TAGS)
    gp_facts = _first_concept_facts(us_gaap, _GROSS_PROFIT_TAGS)
    oi_facts = _first_concept_facts(us_gaap, _OPERATING_INCOME_TAGS)
    ocf_facts = _first_concept_facts(us_gaap, _OCF_TAGS)
    capex_facts = _first_concept_facts(us_gaap, _CAPEX_TAGS)
    eps_facts = _first_concept_facts(us_gaap, _EPS_TAGS)
    equity_facts = _first_concept_facts(us_gaap, _EQUITY_TAGS)

    rev = _pick_latest(rev_facts, prefer_instant=False)
    ni = _pick_latest(ni_facts, prefer_instant=False)
    assets = _pick_latest(assets_facts, prefer_instant=True)
    liab = _pick_latest(liab_facts, prefer_instant=True)
    cash = _pick_latest(cash_facts, prefer_instant=True)
    debt = _pick_latest(debt_facts, prefer_instant=True)
    gp = _pick_latest(gp_facts, prefer_instant=False)
    oi = _pick_latest(oi_facts, prefer_instant=False)
    ocf = _pick_latest(ocf_facts, prefer_instant=False)
    capex = _pick_latest(capex_facts, prefer_instant=False)
    eps = _pick_latest(eps_facts, prefer_instant=False)
    equity = _pick_latest(equity_facts, prefer_instant=True)

    def _val(row: dict[str, Any] | None) -> float | None:
        if row is None:
            return None
        try:
            return float(row["val"])
        except (TypeError, ValueError, KeyError):
            return None

    revenue = _val(rev)
    net_income = _val(ni)
    total_assets = _val(assets)
    total_liabilities = _val(liab)
    total_cash = _val(cash)
    total_debt = _val(debt)
    gross_profit = _val(gp)
    operating_income = _val(oi)
    operating_cf = _val(ocf)
    capex_val = _val(capex)
    eps_trailing = _val(eps)
    equity_val = _val(equity)

    # CapEx often filed as positive outflow; FCF = OCF - |CapEx|
    free_cf = None
    if operating_cf is not None and capex_val is not None:
        free_cf = operating_cf - abs(capex_val)
    elif operating_cf is not None:
        free_cf = operating_cf

    gross_margin = _safe_div(gross_profit, revenue)
    operating_margin = _safe_div(operating_income, revenue)
    debt_to_equity = _safe_div(total_debt, equity_val)

    bs_as_of = None
    for row in (assets, liab, cash, debt):
        if row and row.get("end"):
            bs_as_of = str(row["end"])
            break
    cf_as_of = None
    for row in (ocf, rev, ni):
        if row and row.get("end"):
            cf_as_of = str(row["end"])
            break

    balance_sheet = StatementSummary(
        as_of=bs_as_of,
        total_revenue=revenue,
        net_income=net_income,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        total_cash=total_cash,
        total_debt=total_debt,
    )
    cash_flow = StatementSummary(
        as_of=cf_as_of,
        total_revenue=revenue,
        net_income=net_income,
        operating_cashflow=operating_cf,
        free_cash_flow=free_cf,
        total_cash=total_cash,
        total_debt=total_debt,
    )

    # Drop empty statement objects
    if all(
        getattr(balance_sheet, f) is None
        for f in StatementSummary.model_fields
        if f != "as_of"
    ):
        balance_sheet = None  # type: ignore[assignment]
    if all(
        getattr(cash_flow, f) is None
        for f in StatementSummary.model_fields
        if f != "as_of"
    ):
        cash_flow = None  # type: ignore[assignment]

    as_of_dt = None
    for row in (assets, rev, eps, ocf):
        if row and row.get("filed"):
            try:
                as_of_dt = datetime.fromisoformat(str(row["filed"])).replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                as_of_dt = datetime.now(timezone.utc)
            break

    entity = payload.get("entityName")
    profile = None
    if isinstance(entity, str) and entity.strip():
        from app.schemas.financials import CompanyProfile

        profile = CompanyProfile(name=entity.strip())

    return FinancialMetrics(
        ticker=ticker,
        gross_margin=gross_margin,
        operating_margin=operating_margin,
        free_cash_flow=free_cf,
        debt_to_equity=debt_to_equity,
        eps_trailing=eps_trailing,
        total_cash=total_cash,
        total_debt=total_debt,
        profile=profile,
        revenue_history=_history(rev_facts),
        earnings_history=_history(ni_facts) or _history(eps_facts),
        balance_sheet=balance_sheet,
        cash_flow=cash_flow,
        source_id="sec_xbrl",
        as_of=as_of_dt,
    )


def fetch_sec_xbrl_fundamentals(
    ticker: str,
    *,
    timeout_seconds: float | None = None,
    user_agent: str | None = None,
) -> FinancialMetrics:
    """Fetch SEC companyfacts and map to FinancialMetrics.

    Raises:
        InvalidTickerError, TickerNotFoundError, ToolTimeoutError,
        ToolUpstreamError, ToolParseError
    """
    normalized = normalize_ticker(ticker)
    timeout = (
        float(timeout_seconds)
        if timeout_seconds is not None
        else float(settings.sec_xbrl_timeout_seconds)
    )
    ua = user_agent or settings.sec_user_agent

    def _work() -> FinancialMetrics:
        cik, _title = resolve_ticker_cik(
            normalized, timeout=timeout, user_agent=ua
        )
        url = COMPANYFACTS_URL.format(cik=cik)
        raw = _http_get_bytes(url, timeout=timeout, user_agent=ua)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ToolParseError(
                f"invalid companyfacts JSON for {normalized}"
            ) from exc
        if not isinstance(payload, dict):
            raise ToolParseError(
                f"companyfacts JSON is not an object for {normalized}"
            )
        metrics = parse_companyfacts_json(payload, ticker=normalized)
        # Ensure at least some statement signal
        if (
            metrics.balance_sheet is None
            and metrics.cash_flow is None
            and metrics.eps_trailing is None
            and not metrics.earnings_history
        ):
            raise ToolParseError(
                f"no usable XBRL fundamentals for {normalized}"
            )
        return metrics

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_work)
            metrics = future.result(timeout=timeout)
    except FuturesTimeout as exc:
        logger.warning("sec_xbrl_timeout ticker=%s", normalized)
        raise ToolTimeoutError(
            f"SEC XBRL timeout after {timeout}s for {normalized}"
        ) from exc
    except (TickerNotFoundError, ToolParseError):
        raise
    except HTTPError as exc:
        logger.warning("sec_xbrl_upstream ticker=%s err=%s", normalized, exc)
        raise ToolUpstreamError(
            f"SEC XBRL HTTP error for {normalized}: {exc.code}"
        ) from exc
    except URLError as exc:
        logger.warning("sec_xbrl_upstream ticker=%s err=%s", normalized, exc)
        raise ToolUpstreamError(
            f"SEC XBRL upstream error for {normalized}: {exc.reason}"
        ) from exc
    except Exception as exc:  # noqa: BLE001
        if isinstance(
            exc, (ToolTimeoutError, ToolUpstreamError, TickerNotFoundError, ToolParseError)
        ):
            raise
        logger.warning("sec_xbrl_upstream ticker=%s err=%s", normalized, exc)
        raise ToolUpstreamError(
            f"SEC XBRL upstream error for {normalized}: {exc}"
        ) from exc

    logger.info(
        "sec_xbrl_ok ticker=%s has_bs=%s has_cf=%s eps=%s",
        normalized,
        metrics.balance_sheet is not None,
        metrics.cash_flow is not None,
        metrics.eps_trailing,
    )
    return metrics


def run(ticker: str, **kwargs: Any) -> FinancialMetrics:
    """Scaffold-compatible entrypoint."""
    return fetch_sec_xbrl_fundamentals(ticker, **kwargs)

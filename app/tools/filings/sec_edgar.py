"""SEC EDGAR filings tool.

Fetches recent filing metadata (10-K / 10-Q / 8-K) via data.sec.gov.
Agents must not call HTTP themselves. XBRL fact extraction stays in sec_xbrl.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from datetime import date
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.configs.settings import settings
from app.schemas.filings import SecFiling, SecFilingsBatch
from app.schemas.ticker import normalize_ticker

logger = logging.getLogger(__name__)

COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"

# Primary periodic + material-event forms (include common amendments).
_ALLOWED_FORMS = frozenset(
    {
        "10-K",
        "10-K/A",
        "10-Q",
        "10-Q/A",
        "8-K",
        "8-K/A",
    }
)

_ticker_cik_cache: dict[str, tuple[str, str]] | None = None


class ToolTimeoutError(TimeoutError):
    """SEC request exceeded SEC_TIMEOUT_SECONDS."""


class ToolUpstreamError(RuntimeError):
    """SEC EDGAR upstream failure."""


class ToolParseError(ValueError):
    """SEC payload could not be parsed into SecFilingsBatch."""


class TickerNotFoundError(LookupError):
    """Ticker has no CIK in SEC company_tickers mapping."""


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def _filing_index_url(cik: str, accession_number: str) -> str:
    cik_int = str(int(cik))
    accession_nodash = accession_number.replace("-", "")
    return (
        f"https://www.sec.gov/Archives/edgar/data/"
        f"{cik_int}/{accession_nodash}/"
    )


def parse_submissions_json(
    payload: dict[str, Any],
    *,
    ticker: str,
    cik: str,
    max_filings: int,
) -> SecFilingsBatch:
    """Parse data.sec.gov submissions JSON into SecFilingsBatch (pure, testable)."""
    company_name = payload.get("name")
    if company_name is not None and not isinstance(company_name, str):
        company_name = str(company_name)

    recent = (payload.get("filings") or {}).get("recent") or {}
    if not isinstance(recent, dict):
        raise ToolParseError(f"missing filings.recent for {ticker}")

    forms = recent.get("form") or []
    filing_dates = recent.get("filingDate") or []
    report_dates = recent.get("reportDate") or []
    accessions = recent.get("accessionNumber") or []
    primary_docs = recent.get("primaryDocument") or []

    n = min(len(forms), len(accessions), len(filing_dates))
    if n == 0 and not forms and not accessions:
        return SecFilingsBatch(
            ticker=ticker,
            cik=cik,
            company_name=company_name,
            filings=[],
        )

    filings: list[SecFiling] = []
    for i in range(n):
        form = str(forms[i]).strip()
        if form not in _ALLOWED_FORMS:
            continue
        accession = str(accessions[i]).strip()
        if not accession:
            continue
        primary = None
        if i < len(primary_docs) and primary_docs[i]:
            primary = str(primary_docs[i])
        report = None
        if i < len(report_dates):
            report = _parse_date(str(report_dates[i]) if report_dates[i] else None)
        filings.append(
            SecFiling(
                form=form,
                filing_date=_parse_date(str(filing_dates[i]) if filing_dates[i] else None),
                report_date=report,
                accession_number=accession,
                primary_document=primary,
                url=_filing_index_url(cik, accession),
            )
        )
        if len(filings) >= max_filings:
            break

    return SecFilingsBatch(
        ticker=ticker,
        cik=cik,
        company_name=company_name,
        filings=filings,
    )


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


def _load_ticker_map(
    *,
    timeout: float,
    user_agent: str,
) -> dict[str, tuple[str, str]]:
    """Return ticker → (zero-padded CIK, title). Cached in-process."""
    global _ticker_cik_cache
    if _ticker_cik_cache is not None:
        return _ticker_cik_cache

    raw = _http_get_bytes(
        COMPANY_TICKERS_URL, timeout=timeout, user_agent=user_agent
    )
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ToolParseError("invalid company_tickers.json") from exc

    mapping: dict[str, tuple[str, str]] = {}
    if not isinstance(data, dict):
        raise ToolParseError("company_tickers.json is not an object")
    for row in data.values():
        if not isinstance(row, dict):
            continue
        ticker = str(row.get("ticker") or "").strip().upper()
        cik_raw = row.get("cik_str")
        title = str(row.get("title") or "").strip()
        if not ticker or cik_raw is None:
            continue
        cik = str(int(cik_raw)).zfill(10)
        mapping[ticker] = (cik, title)

    _ticker_cik_cache = mapping
    return mapping


def clear_ticker_map_cache() -> None:
    """Test helper — reset in-process ticker→CIK cache."""
    global _ticker_cik_cache
    _ticker_cik_cache = None


def fetch_sec_filings(
    ticker: str,
    *,
    timeout_seconds: float | None = None,
    max_filings: int | None = None,
    user_agent: str | None = None,
) -> SecFilingsBatch:
    """Fetch recent SEC filing metadata for a ticker.

    Raises:
        InvalidTickerError, TickerNotFoundError, ToolTimeoutError,
        ToolUpstreamError, ToolParseError
    """
    normalized = normalize_ticker(ticker)
    timeout = (
        float(timeout_seconds)
        if timeout_seconds is not None
        else float(settings.sec_timeout_seconds)
    )
    limit = (
        int(max_filings)
        if max_filings is not None
        else int(settings.sec_max_filings)
    )
    ua = user_agent or settings.sec_user_agent

    def _work() -> SecFilingsBatch:
        mapping = _load_ticker_map(timeout=timeout, user_agent=ua)
        if normalized not in mapping:
            raise TickerNotFoundError(f"no SEC CIK for ticker {normalized}")
        cik, _title = mapping[normalized]
        url = SUBMISSIONS_URL.format(cik=cik)
        raw = _http_get_bytes(url, timeout=timeout, user_agent=ua)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ToolParseError(
                f"invalid submissions JSON for {normalized}"
            ) from exc
        if not isinstance(payload, dict):
            raise ToolParseError(
                f"submissions JSON is not an object for {normalized}"
            )
        return parse_submissions_json(
            payload, ticker=normalized, cik=cik, max_filings=limit
        )

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_work)
            batch = future.result(timeout=timeout)
    except FuturesTimeout as exc:
        logger.warning("sec_timeout ticker=%s", normalized)
        raise ToolTimeoutError(
            f"SEC EDGAR timeout after {timeout}s for {normalized}"
        ) from exc
    except (TickerNotFoundError, ToolParseError):
        raise
    except HTTPError as exc:
        logger.warning("sec_upstream ticker=%s err=%s", normalized, exc)
        raise ToolUpstreamError(
            f"SEC EDGAR HTTP error for {normalized}: {exc.code}"
        ) from exc
    except URLError as exc:
        logger.warning("sec_upstream ticker=%s err=%s", normalized, exc)
        raise ToolUpstreamError(
            f"SEC EDGAR upstream error for {normalized}: {exc.reason}"
        ) from exc
    except Exception as exc:  # noqa: BLE001 — wrap unknown network failures
        if isinstance(exc, (ToolTimeoutError, ToolUpstreamError)):
            raise
        logger.warning("sec_upstream ticker=%s err=%s", normalized, exc)
        raise ToolUpstreamError(
            f"SEC EDGAR upstream error for {normalized}: {exc}"
        ) from exc

    logger.info(
        "sec_ok ticker=%s cik=%s filings=%s",
        normalized,
        batch.cik,
        len(batch.filings),
    )
    return batch


def run(ticker: str, **kwargs: Any) -> SecFilingsBatch:
    """Scaffold-compatible entrypoint."""
    return fetch_sec_filings(ticker, **kwargs)

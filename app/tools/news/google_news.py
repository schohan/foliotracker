"""Google News RSS tool.

Fetches structured NewsBatch for a ticker. Agents must not call HTTP themselves.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from app.configs.settings import settings
from app.schemas.news import NewsArticle, NewsBatch
from app.schemas.ticker import normalize_ticker

logger = logging.getLogger(__name__)

GOOGLE_NEWS_RSS = (
    "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
)


class ToolTimeoutError(TimeoutError):
    """News request exceeded NEWS_TIMEOUT_SECONDS."""


class ToolUpstreamError(RuntimeError):
    """Google News upstream failure."""


class ToolParseError(ValueError):
    """News RSS payload could not be parsed into NewsBatch."""


def _parse_pub_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except (TypeError, ValueError, IndexError):
        return None


def _text(el: ET.Element | None) -> str:
    if el is None or el.text is None:
        return ""
    return el.text.strip()


def parse_google_news_rss(xml_text: str, ticker: str) -> NewsBatch:
    """Parse Google News RSS XML into a NewsBatch (pure, testable)."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ToolParseError(f"invalid RSS XML for {ticker}: {exc}") from exc

    channel = root.find("channel")
    if channel is None:
        # Some feeds use Atom-style; still accept top-level items
        items = root.findall("item")
    else:
        items = channel.findall("item")

    articles: list[NewsArticle] = []
    for item in items:
        title = _text(item.find("title"))
        link = _text(item.find("link"))
        if not title or not link:
            continue
        source_el = item.find("source")
        publisher = _text(source_el) if source_el is not None else None
        published_at = _parse_pub_date(_text(item.find("pubDate")) or None)
        articles.append(
            NewsArticle(
                title=title,
                url=link,
                published_at=published_at,
                publisher=publisher or None,
            )
        )

    return NewsBatch(ticker=ticker, articles=articles)


def _fetch_rss_bytes(url: str, timeout: float) -> bytes:
    req = Request(
        url,
        headers={
            "User-Agent": "FolioTracker/0.1 (+https://github.com/foliotracker)",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
    )
    with urlopen(req, timeout=timeout) as resp:  # noqa: S310 — fixed Google News host
        return resp.read()


def fetch_google_news(
    ticker: str,
    *,
    timeout_seconds: float | None = None,
) -> NewsBatch:
    """Fetch recent Google News headlines for a ticker via RSS.

    Args:
        ticker: Equity symbol (validated/normalized).
        timeout_seconds: Override default NEWS_TIMEOUT_SECONDS.

    Raises:
        InvalidTickerError, ToolTimeoutError, ToolUpstreamError, ToolParseError
    """
    normalized = normalize_ticker(ticker)
    timeout = (
        float(timeout_seconds)
        if timeout_seconds is not None
        else float(settings.news_timeout_seconds)
    )
    query = quote_plus(f"{normalized} stock")
    url = GOOGLE_NEWS_RSS.format(query=query)

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_fetch_rss_bytes, url, timeout)
            raw = future.result(timeout=timeout)
    except FuturesTimeout as exc:
        logger.warning("news_timeout ticker=%s", normalized)
        raise ToolTimeoutError(
            f"Google News timeout after {timeout}s for {normalized}"
        ) from exc
    except ToolParseError:
        raise
    except HTTPError as exc:
        logger.warning("news_upstream ticker=%s err=%s", normalized, exc)
        raise ToolUpstreamError(
            f"Google News HTTP error for {normalized}: {exc.code}"
        ) from exc
    except URLError as exc:
        logger.warning("news_upstream ticker=%s err=%s", normalized, exc)
        raise ToolUpstreamError(
            f"Google News upstream error for {normalized}: {exc.reason}"
        ) from exc
    except Exception as exc:  # noqa: BLE001 — wrap unknown network failures
        logger.warning("news_upstream ticker=%s err=%s", normalized, exc)
        raise ToolUpstreamError(
            f"Google News upstream error for {normalized}: {exc}"
        ) from exc

    try:
        xml_text = raw.decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        raise ToolParseError(f"could not decode RSS for {normalized}") from exc

    batch = parse_google_news_rss(xml_text, normalized)
    logger.info(
        "news_ok ticker=%s articles=%s",
        normalized,
        len(batch.articles),
    )
    return batch


def run(ticker: str, **kwargs: Any) -> NewsBatch:
    """Scaffold-compatible entrypoint."""
    return fetch_google_news(ticker, **kwargs)

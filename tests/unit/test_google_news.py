"""Google News RSS tool — unit tests with fixture XML (no live network)."""

from __future__ import annotations

from concurrent.futures import TimeoutError as FuturesTimeout
from datetime import timezone

import pytest

from app.schemas.news import NewsBatch
from app.tools.news import google_news
from app.tools.news.google_news import (
    ToolParseError,
    ToolTimeoutError,
    ToolUpstreamError,
    fetch_google_news,
    parse_google_news_rss,
)

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Google News</title>
    <item>
      <title>NVDA stock surges on AI demand</title>
      <link>https://example.com/nvda-surge</link>
      <pubDate>Mon, 20 Jul 2026 12:00:00 GMT</pubDate>
      <source url="https://example.com">Example Wire</source>
    </item>
    <item>
      <title>Traders watch chipmakers</title>
      <link>https://example.com/chips</link>
      <pubDate>Sun, 19 Jul 2026 09:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""


def test_parse_google_news_rss_extracts_articles() -> None:
    batch = parse_google_news_rss(SAMPLE_RSS, "NVDA")
    assert isinstance(batch, NewsBatch)
    assert batch.ticker == "NVDA"
    assert len(batch.articles) == 2
    assert batch.articles[0].title.startswith("NVDA stock")
    assert batch.articles[0].url == "https://example.com/nvda-surge"
    assert batch.articles[0].publisher == "Example Wire"
    assert batch.articles[0].published_at is not None
    assert batch.articles[0].published_at.tzinfo == timezone.utc


def test_parse_invalid_xml_raises() -> None:
    with pytest.raises(ToolParseError):
        parse_google_news_rss("<not-rss", "NVDA")


def test_fetch_google_news_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        google_news,
        "_fetch_rss_bytes",
        lambda url, timeout: SAMPLE_RSS.encode("utf-8"),
    )
    batch = fetch_google_news("nvda")
    assert batch.ticker == "NVDA"
    assert len(batch.articles) == 2


def test_fetch_google_news_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
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

    monkeypatch.setattr(google_news, "ThreadPoolExecutor", BoomPool)
    with pytest.raises(ToolTimeoutError):
        fetch_google_news("AAPL", timeout_seconds=0.001)


def test_fetch_google_news_upstream(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(url: str, timeout: float) -> bytes:
        raise google_news.URLError("dns fail")

    monkeypatch.setattr(google_news, "_fetch_rss_bytes", boom)
    with pytest.raises(ToolUpstreamError):
        fetch_google_news("AAPL")

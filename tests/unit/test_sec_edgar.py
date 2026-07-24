"""SEC EDGAR tool — unit tests with fixture JSON (no live network)."""

from __future__ import annotations

from concurrent.futures import TimeoutError as FuturesTimeout
from datetime import date

import pytest

from app.schemas.filings import SecFilingsBatch
from app.tools.filings import sec_edgar
from app.tools.filings.sec_edgar import (
    TickerNotFoundError,
    ToolParseError,
    ToolTimeoutError,
    ToolUpstreamError,
    clear_ticker_map_cache,
    fetch_sec_filings,
    parse_submissions_json,
)

SAMPLE_TICKERS = {
    "0": {"cik_str": 1045810, "ticker": "NVDA", "title": "NVIDIA CORP"},
    "1": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
}

SAMPLE_SUBMISSIONS = {
    "cik": "0001045810",
    "name": "NVIDIA CORP",
    "filings": {
        "recent": {
            "form": ["8-K", "10-Q", "4", "10-K", "8-K"],
            "filingDate": [
                "2026-07-01",
                "2026-05-28",
                "2026-05-20",
                "2026-02-26",
                "2026-01-15",
            ],
            "reportDate": [
                "2026-07-01",
                "2026-04-27",
                "",
                "2026-01-26",
                "2026-01-15",
            ],
            "accessionNumber": [
                "0001045810-26-000111",
                "0001045810-26-000099",
                "0001045810-26-000088",
                "0001045810-26-000055",
                "0001045810-26-000011",
            ],
            "primaryDocument": [
                "nvda-20260701.htm",
                "nvda-20260427.htm",
                "xslF345X05/primary_doc.xml",
                "nvda-20260126.htm",
                "nvda-20260115.htm",
            ],
        }
    },
}


@pytest.fixture(autouse=True)
def _reset_ticker_cache() -> None:
    clear_ticker_map_cache()
    yield
    clear_ticker_map_cache()


def test_parse_submissions_filters_forms_and_caps() -> None:
    batch = parse_submissions_json(
        SAMPLE_SUBMISSIONS,
        ticker="NVDA",
        cik="0001045810",
        max_filings=3,
    )
    assert isinstance(batch, SecFilingsBatch)
    assert batch.ticker == "NVDA"
    assert batch.cik == "0001045810"
    assert batch.company_name == "NVIDIA CORP"
    assert len(batch.filings) == 3
    assert [f.form for f in batch.filings] == ["8-K", "10-Q", "10-K"]
    assert batch.filings[0].filing_date == date(2026, 7, 1)
    assert "0001045810" in batch.filings[0].url
    assert "000104581026000111" in batch.filings[0].url


def test_parse_submissions_missing_recent_raises() -> None:
    with pytest.raises(ToolParseError):
        parse_submissions_json(
            {"name": "X", "filings": {"recent": "bad"}},
            ticker="NVDA",
            cik="0001045810",
            max_filings=5,
        )


def test_fetch_sec_filings_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_get(url: str, *, timeout: float, user_agent: str) -> bytes:
        calls.append(url)
        if "company_tickers" in url:
            import json

            return json.dumps(SAMPLE_TICKERS).encode()
        import json

        return json.dumps(SAMPLE_SUBMISSIONS).encode()

    monkeypatch.setattr(sec_edgar, "_http_get_bytes", fake_get)
    batch = fetch_sec_filings("nvda", max_filings=2)
    assert batch.ticker == "NVDA"
    assert len(batch.filings) == 2
    assert len(calls) == 2


def test_fetch_sec_filings_ticker_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url: str, *, timeout: float, user_agent: str) -> bytes:
        import json

        return json.dumps(SAMPLE_TICKERS).encode()

    monkeypatch.setattr(sec_edgar, "_http_get_bytes", fake_get)
    with pytest.raises(TickerNotFoundError):
        fetch_sec_filings("ZZZZ")


def test_fetch_sec_filings_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
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

    monkeypatch.setattr(sec_edgar, "ThreadPoolExecutor", BoomPool)
    with pytest.raises(ToolTimeoutError):
        fetch_sec_filings("AAPL", timeout_seconds=0.001)


def test_fetch_sec_filings_upstream(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(url: str, *, timeout: float, user_agent: str) -> bytes:
        raise sec_edgar.URLError("dns fail")

    monkeypatch.setattr(sec_edgar, "_http_get_bytes", boom)
    with pytest.raises(ToolUpstreamError):
        fetch_sec_filings("AAPL")

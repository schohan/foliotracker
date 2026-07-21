"""Ticker validation — runnable now (pure contract)."""

from __future__ import annotations

import pytest

from app.schemas.ticker import InvalidTickerError, normalize_ticker


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("nvda", "NVDA"),
        ("NVDA", "NVDA"),
        ("  aapl  ", "AAPL"),
        ("BRK.B", "BRK.B"),
        ("brk.b", "BRK.B"),
    ],
)
def test_normalize_ticker_ok(raw: str, expected: str) -> None:
    assert normalize_ticker(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [None, "", "   ", "NVD A", "NVDA!", "toolongtickerx", "../etc", "nvda;drop"],
)
def test_normalize_ticker_rejects(raw: str | None) -> None:
    with pytest.raises(InvalidTickerError):
        normalize_ticker(raw)

"""Ticker validation helpers (Phase 0 contract — pure, no I/O)."""

from __future__ import annotations

import re

# Allows BRK.B-style symbols; uppercase A–Z, optional .SUFFIX
TICKER_PATTERN = re.compile(r"^[A-Z]{1,10}(\.[A-Z]{1,3})?$")


class InvalidTickerError(ValueError):
    """Ticker missing, empty, or fails Phase 0 format validation."""


def normalize_ticker(raw: str | None) -> str:
    """Validate and normalize a ticker to uppercase.

    Raises:
        InvalidTickerError: nil, empty, or invalid format.
    """
    if raw is None:
        raise InvalidTickerError("ticker is required")
    cleaned = raw.strip().upper()
    if not cleaned:
        raise InvalidTickerError("ticker is required")
    if not TICKER_PATTERN.match(cleaned):
        raise InvalidTickerError(f"invalid ticker format: {raw!r}")
    return cleaned

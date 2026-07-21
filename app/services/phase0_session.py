"""Phase 0 session helpers (5A — clear prior research state)."""

from __future__ import annotations

from typing import Any

from app.schemas.ticker import normalize_ticker

_CLEAR_KEYS = (
    "financial_metrics",
    "evidence_bundle",
    "thesis",
    "phase0_status",
    "cache_hit",
)


def clear_research_session(state: dict[str, Any]) -> dict[str, Any]:
    """Clear prior research keys to avoid cross-ticker contamination."""
    cleared = dict(state)
    for key in _CLEAR_KEYS:
        cleared[key] = None
    return cleared


def new_research_session(state: dict[str, Any], ticker: str) -> dict[str, Any]:
    """Clear prior keys and set normalized ticker for a new run."""
    started = clear_research_session(state)
    started["ticker"] = normalize_ticker(ticker)
    started["phase0_status"] = "running"
    return started

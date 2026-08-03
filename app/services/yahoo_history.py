"""Yahoo daily close history helpers (shared by Risk + Brief).

Pure parse/calc over source-cache payloads. Live refetch is caller's job
via ``cached_fetch`` / ``fetch_financial_metrics``.
"""

from __future__ import annotations

import math
from typing import Any

from app.configs.settings import Settings, settings as default_settings
from app.services.source_cache import source_cache_lookup
from app.services.source_registry import SOURCE_YAHOO, get_source

# |daily %| → move_score (design table).
MOVE_GATE_ABS = 0.05  # 5%


def parse_history_closes(payload: dict[str, Any] | None) -> list[tuple[str, float]] | None:
    """Extract ``history_closes`` from a Yahoo source-cache payload."""
    if not payload or not isinstance(payload, dict):
        return None
    raw = payload.get("history_closes")
    if not isinstance(raw, list) or not raw:
        return None
    out: list[tuple[str, float]] = []
    for item in raw:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            date_s, px = item[0], item[1]
        elif isinstance(item, dict):
            date_s, px = item.get("date"), item.get("close")
        else:
            continue
        if date_s is None or px is None:
            continue
        try:
            price = float(px)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(price) or price <= 0:
            continue
        out.append((str(date_s)[:10], price))
    return out or None


def lookup_history_closes(
    ticker: str,
    *,
    app_settings: Settings | None = None,
) -> list[tuple[str, float]] | None:
    """Read Yahoo per-source cache (stale OK). No live refetch."""
    s = app_settings if app_settings is not None else default_settings
    try:
        cfg = get_source(SOURCE_YAHOO, s)
        ttl = cfg.ttl_seconds
    except Exception:  # noqa: BLE001 — registry miss should not break callers
        ttl = s.yahoo_source_ttl_seconds
    envelope = source_cache_lookup(
        SOURCE_YAHOO,
        ticker,
        ttl_seconds=ttl,
        cache_root=s.source_cache_dir,
        allow_stale=True,
        app_settings=s,
    )
    if envelope is None:
        return None
    return parse_history_closes(envelope.payload)


def daily_returns(closes: list[tuple[str, float]]) -> dict[str, float]:
    """Map date → simple return vs prior close (keyed by later date)."""
    ordered = sorted(closes, key=lambda row: row[0])
    returns: dict[str, float] = {}
    for i in range(1, len(ordered)):
        _prev_d, prev_px = ordered[i - 1]
        cur_d, cur_px = ordered[i]
        if prev_px <= 0:
            continue
        ret = (cur_px - prev_px) / prev_px
        if math.isfinite(ret):
            returns[cur_d] = ret
    return returns


def last_session_daily_return(
    closes: list[tuple[str, float]] | None,
) -> float | None:
    """Prior regular-session close → latest available regular-session close.

    Weekend / pre-market Generate uses the last completed session move.
    """
    if not closes or len(closes) < 2:
        return None
    ordered = sorted(closes, key=lambda row: row[0])
    prev_px = ordered[-2][1]
    cur_px = ordered[-1][1]
    if prev_px <= 0:
        return None
    ret = (cur_px - prev_px) / prev_px
    if not math.isfinite(ret):
        return None
    return ret


def move_score(daily_return: float | None) -> int | None:
    """Map |daily return| fraction to 1–5 (design table). None if unknown."""
    if daily_return is None:
        return None
    pct = abs(daily_return) * 100.0
    if pct >= 15.0:
        return 5
    if pct >= 12.0:
        return 4
    if pct >= 8.0:
        return 3
    if pct >= 5.0:
        return 2
    if pct > 0.0:
        return 1
    return 0


def passes_move_gate(daily_return: float | None) -> bool:
    """True when |daily return| ≥ 5%."""
    if daily_return is None:
        return False
    return abs(daily_return) >= MOVE_GATE_ABS

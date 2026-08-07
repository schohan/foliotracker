"""Per-source file cache + local rate budgets (Phase 2C.1)."""

from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.configs.settings import Settings, settings as default_settings
from app.schemas.sources import DataSourceConfig, SourceCacheEnvelope

logger = logging.getLogger(__name__)

_rate_lock = threading.Lock()

# When a live fetch is only blocked by min-interval and the remaining wait is
# at most this many seconds, sleep then acquire (bulk refresh pacing).
_MIN_INTERVAL_WAIT_CAP_SECONDS = 60.0


def _source_dir(source_id: str, cache_root: Path) -> Path:
    return cache_root / source_id


def _payload_path(source_id: str, ticker: str, cache_root: Path) -> Path:
    return _source_dir(source_id, cache_root) / f"{ticker.upper()}.json"


def _rate_path(source_id: str, cache_root: Path) -> Path:
    return _source_dir(source_id, cache_root) / "_rate.json"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def source_cache_lookup(
    source_id: str,
    ticker: str,
    *,
    ttl_seconds: int,
    cache_root: Path | None = None,
    allow_stale: bool = False,
    app_settings: Settings | None = None,
) -> SourceCacheEnvelope | None:
    """Return cached envelope if fresh (or any if allow_stale). Corrupt → None."""
    s = app_settings if app_settings is not None else default_settings
    root = Path(cache_root) if cache_root is not None else s.source_cache_dir
    path = _payload_path(source_id, ticker, root)
    if not path.exists():
        logger.info(
            "source_cache_miss source=%s ticker=%s reason=missing",
            source_id,
            ticker.upper(),
        )
        return None

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        envelope = SourceCacheEnvelope.model_validate(raw)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.warning(
            "source_cache_corrupt source=%s ticker=%s err=%s",
            source_id,
            ticker.upper(),
            exc,
        )
        return None

    fetched_at = envelope.fetched_at
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)
    age = (_now() - fetched_at).total_seconds()
    fresh = ttl_seconds > 0 and age < ttl_seconds
    if fresh:
        logger.info(
            "source_cache_hit source=%s ticker=%s age_s=%.1f",
            source_id,
            ticker.upper(),
            age,
        )
        return envelope

    if allow_stale:
        logger.info(
            "source_cache_stale source=%s ticker=%s age_s=%.1f ttl=%s",
            source_id,
            ticker.upper(),
            age,
            ttl_seconds,
        )
        return envelope

    logger.info(
        "source_cache_miss source=%s ticker=%s reason=expired age_s=%.1f ttl=%s",
        source_id,
        ticker.upper(),
        age,
        ttl_seconds,
    )
    return None


def source_cache_store(
    source_id: str,
    ticker: str,
    payload: dict[str, Any],
    *,
    cache_root: Path | None = None,
    app_settings: Settings | None = None,
    status: str = "ok",
) -> None:
    """Persist a successful source payload. IO failures are warnings."""
    s = app_settings if app_settings is not None else default_settings
    root = Path(cache_root) if cache_root is not None else s.source_cache_dir
    directory = _source_dir(source_id, root)
    try:
        directory.mkdir(parents=True, exist_ok=True)
        envelope = SourceCacheEnvelope(
            source_id=source_id,
            ticker=ticker.upper(),
            fetched_at=_now(),
            status=status,
            payload=payload,
        )
        path = _payload_path(source_id, ticker, root)
        path.write_text(
            envelope.model_dump_json(indent=2),
            encoding="utf-8",
        )
        logger.info(
            "source_cache_store source=%s ticker=%s path=%s",
            source_id,
            ticker.upper(),
            path,
        )
    except OSError as exc:
        logger.warning(
            "source_cache_store_failed source=%s ticker=%s err=%s",
            source_id,
            ticker.upper(),
            exc,
        )


def _prune_timestamps(timestamps: list[float], now_ts: float, window: int) -> list[float]:
    cutoff = now_ts - window
    return [t for t in timestamps if t >= cutoff]


def _budget_block_reason(
    cfg: DataSourceConfig,
    timestamps: list[float],
    now_ts: float,
) -> str | None:
    """Return why a live fetch is blocked, or None if allowed."""
    if cfg.rate_limit_calls > 0 and len(timestamps) >= cfg.rate_limit_calls:
        return "count"
    min_interval = float(cfg.rate_limit_min_interval_seconds or 0)
    if min_interval > 0 and timestamps:
        elapsed = now_ts - timestamps[-1]
        if elapsed < min_interval:
            return "min_interval"
    return None


def _seconds_until_min_interval(
    cfg: DataSourceConfig,
    timestamps: list[float],
    now_ts: float,
) -> float:
    min_interval = float(cfg.rate_limit_min_interval_seconds or 0)
    if min_interval <= 0 or not timestamps:
        return 0.0
    remaining = min_interval - (now_ts - timestamps[-1])
    return max(0.0, remaining)


def rate_budget_available(
    cfg: DataSourceConfig,
    *,
    cache_root: Path | None = None,
    app_settings: Settings | None = None,
) -> bool:
    """True if a live fetch is allowed under the soft local budget."""
    if cfg.rate_limit_calls <= 0 and float(cfg.rate_limit_min_interval_seconds or 0) <= 0:
        return True

    s = app_settings if app_settings is not None else default_settings
    root = Path(cache_root) if cache_root is not None else s.source_cache_dir
    path = _rate_path(cfg.source_id, root)
    now_ts = _now().timestamp()
    window = cfg.rate_limit_window_seconds

    with _rate_lock:
        timestamps = _prune_timestamps(_read_timestamps(path), now_ts, window)
        return _budget_block_reason(cfg, timestamps, now_ts) is None


def rate_budget_consume(
    cfg: DataSourceConfig,
    *,
    cache_root: Path | None = None,
    app_settings: Settings | None = None,
) -> None:
    """Record one live fetch against the soft local budget."""
    if cfg.rate_limit_calls <= 0 and float(cfg.rate_limit_min_interval_seconds or 0) <= 0:
        return

    s = app_settings if app_settings is not None else default_settings
    root = Path(cache_root) if cache_root is not None else s.source_cache_dir
    path = _rate_path(cfg.source_id, root)
    now_ts = _now().timestamp()
    window = cfg.rate_limit_window_seconds

    with _rate_lock:
        _write_consume(path, cfg.source_id, now_ts, window)


def rate_budget_try_acquire(
    cfg: DataSourceConfig,
    *,
    cache_root: Path | None = None,
    app_settings: Settings | None = None,
    allow_wait: bool = True,
) -> bool:
    """Atomically reserve one live-fetch slot (count + min-interval).

    When blocked only by min-interval and the remaining wait is ≤ 60s,
    optionally sleep then retry so bulk refresh paces short gaps without
    racing parallel workers. Longer gaps (e.g. AV daily pacing) return
    False immediately so callers can serve stale cache.
    """
    if cfg.rate_limit_calls <= 0 and float(cfg.rate_limit_min_interval_seconds or 0) <= 0:
        return True

    s = app_settings if app_settings is not None else default_settings
    root = Path(cache_root) if cache_root is not None else s.source_cache_dir
    path = _rate_path(cfg.source_id, root)
    window = cfg.rate_limit_window_seconds

    while True:
        sleep_for = 0.0
        with _rate_lock:
            now_ts = _now().timestamp()
            timestamps = _prune_timestamps(_read_timestamps(path), now_ts, window)
            reason = _budget_block_reason(cfg, timestamps, now_ts)
            if reason is None:
                _write_consume(path, cfg.source_id, now_ts, window)
                return True
            if reason == "count":
                return False
            # min_interval
            remaining = _seconds_until_min_interval(cfg, timestamps, now_ts)
            if (
                allow_wait
                and remaining > 0
                and remaining <= _MIN_INTERVAL_WAIT_CAP_SECONDS
            ):
                sleep_for = remaining
            else:
                return False
        # Sleep outside the lock so other sources can proceed.
        logger.info(
            "rate_budget_wait source=%s wait_s=%.2f",
            cfg.source_id,
            sleep_for,
        )
        time.sleep(sleep_for)


def _write_consume(path: Path, source_id: str, now_ts: float, window: int) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        timestamps = _prune_timestamps(_read_timestamps(path), now_ts, window)
        timestamps.append(now_ts)
        path.write_text(
            json.dumps({"calls": timestamps}, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.warning(
            "rate_budget_consume_failed source=%s err=%s",
            source_id,
            exc,
        )


def _read_timestamps(path: Path) -> list[float]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return []
        calls = data.get("calls", [])
        if not isinstance(calls, list):
            return []
        out: list[float] = []
        for item in calls:
            try:
                out.append(float(item))
            except (TypeError, ValueError):
                continue
        return out
    except (OSError, json.JSONDecodeError, TypeError):
        return []

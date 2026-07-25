"""Per-source file cache + local rate budgets (Phase 2C.1)."""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.configs.settings import Settings, settings as default_settings
from app.schemas.sources import DataSourceConfig, SourceCacheEnvelope

logger = logging.getLogger(__name__)

_rate_lock = threading.Lock()


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


def rate_budget_available(
    cfg: DataSourceConfig,
    *,
    cache_root: Path | None = None,
    app_settings: Settings | None = None,
) -> bool:
    """True if a live fetch is allowed under the soft local budget."""
    if cfg.rate_limit_calls <= 0:
        return True

    s = app_settings if app_settings is not None else default_settings
    root = Path(cache_root) if cache_root is not None else s.source_cache_dir
    path = _rate_path(cfg.source_id, root)
    now = _now()
    window = cfg.rate_limit_window_seconds

    with _rate_lock:
        timestamps = _read_timestamps(path)
        cutoff = now.timestamp() - window
        timestamps = [t for t in timestamps if t >= cutoff]
        return len(timestamps) < cfg.rate_limit_calls


def rate_budget_consume(
    cfg: DataSourceConfig,
    *,
    cache_root: Path | None = None,
    app_settings: Settings | None = None,
) -> None:
    """Record one live fetch against the soft local budget."""
    if cfg.rate_limit_calls <= 0:
        return

    s = app_settings if app_settings is not None else default_settings
    root = Path(cache_root) if cache_root is not None else s.source_cache_dir
    path = _rate_path(cfg.source_id, root)
    now = _now()
    window = cfg.rate_limit_window_seconds

    with _rate_lock:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            timestamps = _read_timestamps(path)
            cutoff = now.timestamp() - window
            timestamps = [t for t in timestamps if t >= cutoff]
            timestamps.append(now.timestamp())
            path.write_text(
                json.dumps({"calls": timestamps}, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning(
                "rate_budget_consume_failed source=%s err=%s",
                cfg.source_id,
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

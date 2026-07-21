"""Local TTL file cache for Phase0Result."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.configs.settings import settings
from app.schemas.phase0 import Phase0Result, Phase0Status

logger = logging.getLogger(__name__)


def _cache_path(ticker: str, cache_dir: Path) -> Path:
    return cache_dir / f"{ticker.upper()}.json"


def _read_envelope(path: Path) -> dict[str, Any] | None:
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict) or "cached_at" not in data or "result" not in data:
            return None
        return data
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        logger.warning("cache_corrupt path=%s err=%s", path, exc)
        return None


def cache_lookup(
    ticker: str,
    *,
    cache_dir: Path | None = None,
    ttl_seconds: int | None = None,
) -> Phase0Result | None:
    """Return cached Phase0Result if fresh; else None (miss/expired/corrupt)."""
    directory = Path(cache_dir) if cache_dir is not None else settings.phase0_cache_dir
    ttl = settings.phase0_cache_ttl_seconds if ttl_seconds is None else int(ttl_seconds)
    path = _cache_path(ticker, directory)
    if not path.exists():
        logger.info("cache_miss ticker=%s reason=missing", ticker.upper())
        return None

    envelope = _read_envelope(path)
    if envelope is None:
        logger.info("cache_miss ticker=%s reason=corrupt", ticker.upper())
        return None

    try:
        cached_at = datetime.fromisoformat(envelope["cached_at"])
        if cached_at.tzinfo is None:
            cached_at = cached_at.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - cached_at).total_seconds()
        if age >= ttl or ttl <= 0:
            logger.info(
                "cache_miss ticker=%s reason=expired age_s=%.1f ttl=%s",
                ticker.upper(),
                age,
                ttl,
            )
            return None
        result = Phase0Result.model_validate(envelope["result"])
    except Exception as exc:  # noqa: BLE001 — corrupt/invalid cache → miss
        logger.warning("cache_miss ticker=%s reason=invalid err=%s", ticker.upper(), exc)
        return None

    # Fresh request_id on every serve; always mark cache_hit
    served = result.model_copy(
        update={
            "cache_hit": True,
            "request_id": str(uuid.uuid4()),
        }
    )
    logger.info(
        "cache_hit ticker=%s age_s=%.1f request_id=%s",
        ticker.upper(),
        age,
        served.request_id,
    )
    return served


def cache_store(
    result: Phase0Result,
    *,
    cache_dir: Path | None = None,
) -> None:
    """Persist ok/partial results. Never store errors. IO failures are warnings."""
    if result.status == Phase0Status.ERROR:
        logger.info("cache_skip_error ticker=%s", result.ticker)
        return

    directory = Path(cache_dir) if cache_dir is not None else settings.phase0_cache_dir
    try:
        directory.mkdir(parents=True, exist_ok=True)
        # Store with cache_hit=false so reloads don't bake in a prior hit flag
        to_store = result.model_copy(update={"cache_hit": False})
        envelope = {
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "result": to_store.model_dump(mode="json"),
        }
        path = _cache_path(result.ticker, directory)
        path.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
        logger.info("cache_store ticker=%s path=%s", result.ticker, path)
    except OSError as exc:
        logger.warning("cache_store_failed ticker=%s err=%s", result.ticker, exc)

"""Fetch through DataSource registry + per-source cache (Phase 2C.1)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TypeVar

from pydantic import BaseModel

from app.configs.settings import Settings, settings as default_settings
from app.schemas.sources import SourceFetchMeta, SourceFetchResult
from app.services.source_cache import (
    rate_budget_available,
    rate_budget_consume,
    source_cache_lookup,
    source_cache_store,
)
from app.services.source_registry import get_source

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class SourceDisabledError(RuntimeError):
    """Source is disabled in the registry."""


class SourceRateLimitedError(RuntimeError):
    """Live fetch skipped: rate budget exhausted and no stale cache."""


def cached_fetch(
    source_id: str,
    ticker: str,
    fetch_fn: Callable[[], T],
    model_cls: type[T],
    *,
    app_settings: Settings | None = None,
    force_refresh: bool = False,
) -> SourceFetchResult:
    """Return domain model from fresh cache, stale (if rate-limited), or live fetch.

    ASCII flow::

        force_refresh?
          yes → (skip fresh) rate budget → fetch_fn() → store
        lookup fresh?
          yes → return (cache_hit)
          no  → rate budget ok?
                  no → stale available? yes → return stale
                                       no  → SourceRateLimitedError
                  yes → fetch_fn() → store → return
    """
    s = app_settings if app_settings is not None else default_settings
    cfg = get_source(source_id, s)
    if not cfg.enabled:
        raise SourceDisabledError(f"source {source_id} is disabled")

    root = s.source_cache_dir
    if not force_refresh:
        fresh = source_cache_lookup(
            source_id,
            ticker,
            ttl_seconds=cfg.ttl_seconds,
            cache_root=root,
            allow_stale=False,
            app_settings=s,
        )
        if fresh is not None and fresh.status == "ok":
            data = model_cls.model_validate(fresh.payload)
            return SourceFetchResult(
                data=data,
                meta=SourceFetchMeta(source_id=source_id, cache_hit=True),
            )

    if not rate_budget_available(cfg, cache_root=root, app_settings=s):
        stale = source_cache_lookup(
            source_id,
            ticker,
            ttl_seconds=cfg.ttl_seconds,
            cache_root=root,
            allow_stale=True,
            app_settings=s,
        )
        if stale is not None and stale.status == "ok":
            data = model_cls.model_validate(stale.payload)
            logger.warning(
                "source_rate_limited_stale source=%s ticker=%s",
                source_id,
                ticker.upper(),
            )
            return SourceFetchResult(
                data=data,
                meta=SourceFetchMeta(
                    source_id=source_id,
                    cache_hit=True,
                    stale=True,
                    rate_limited=True,
                ),
            )
        raise SourceRateLimitedError(
            f"source {source_id} rate budget exhausted for {ticker.upper()}"
        )

    rate_budget_consume(cfg, cache_root=root, app_settings=s)
    data = fetch_fn()
    source_cache_store(
        source_id,
        ticker,
        data.model_dump(mode="json"),
        cache_root=root,
        app_settings=s,
    )
    return SourceFetchResult(
        data=data,
        meta=SourceFetchMeta(source_id=source_id, cache_hit=False),
    )

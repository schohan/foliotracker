"""Per-source cache + rate budgets (Phase 2C.1)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.configs.settings import Settings
from app.schemas.sources import DataSourceConfig
from app.services.source_cache import (
    rate_budget_available,
    rate_budget_consume,
    source_cache_lookup,
    source_cache_store,
)


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        google_api_key=None,
        source_cache_dir=tmp_path,
    )


def test_source_cache_miss_store_hit(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    assert (
        source_cache_lookup(
            "yahoo",
            "NVDA",
            ttl_seconds=3600,
            app_settings=s,
        )
        is None
    )

    source_cache_store(
        "yahoo",
        "NVDA",
        {"ticker": "NVDA", "pe_ratio": 40.0},
        app_settings=s,
    )
    hit = source_cache_lookup(
        "yahoo",
        "nvda",
        ttl_seconds=3600,
        app_settings=s,
    )
    assert hit is not None
    assert hit.payload["pe_ratio"] == 40.0
    assert hit.ticker == "NVDA"


def test_source_cache_expired_is_miss_unless_stale(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    source_cache_store(
        "yahoo",
        "NVDA",
        {"ticker": "NVDA"},
        app_settings=s,
    )
    path = tmp_path / "yahoo" / "NVDA.json"
    # Backdate fetched_at
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    old = datetime.now(timezone.utc) - timedelta(hours=2)
    data["fetched_at"] = old.isoformat()
    path.write_text(json.dumps(data), encoding="utf-8")

    assert (
        source_cache_lookup(
            "yahoo",
            "NVDA",
            ttl_seconds=3600,
            app_settings=s,
            allow_stale=False,
        )
        is None
    )
    stale = source_cache_lookup(
        "yahoo",
        "NVDA",
        ttl_seconds=3600,
        app_settings=s,
        allow_stale=True,
    )
    assert stale is not None


def test_source_cache_corrupt_is_miss(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    bad = tmp_path / "yahoo"
    bad.mkdir(parents=True)
    (bad / "NVDA.json").write_text("{not-json", encoding="utf-8")
    assert (
        source_cache_lookup(
            "yahoo",
            "NVDA",
            ttl_seconds=3600,
            app_settings=s,
        )
        is None
    )


def test_rate_budget_exhausted(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    cfg = DataSourceConfig(
        source_id="yahoo",
        confidence=0.95,
        ttl_seconds=3600,
        rate_limit_calls=2,
        rate_limit_window_seconds=3600,
    )
    assert rate_budget_available(cfg, app_settings=s) is True
    rate_budget_consume(cfg, app_settings=s)
    rate_budget_consume(cfg, app_settings=s)
    assert rate_budget_available(cfg, app_settings=s) is False


def test_rate_budget_unlimited(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    cfg = DataSourceConfig(
        source_id="yahoo",
        confidence=0.95,
        ttl_seconds=3600,
        rate_limit_calls=0,
        rate_limit_window_seconds=3600,
    )
    for _ in range(5):
        assert rate_budget_available(cfg, app_settings=s) is True
        rate_budget_consume(cfg, app_settings=s)

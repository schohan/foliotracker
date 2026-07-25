"""Settings defaults for Phase 0 — runnable now."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.configs.settings import Settings


def test_settings_phase0_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "PHASE0_CACHE_TTL_SECONDS",
        "CACHE_TTL_SECONDS",
        "PHASE0_CACHE_DIR",
        "CACHE_DIR",
        "SOURCE_CACHE_DIR",
        "YAHOO_SOURCE_TTL_SECONDS",
        "NEWS_SOURCE_TTL_SECONDS",
        "SEC_SOURCE_TTL_SECONDS",
        "YAHOO_TIMEOUT_SECONDS",
        "NEWS_TIMEOUT_SECONDS",
        "NEWS_MAX_ARTICLES",
    ):
        monkeypatch.delenv(key, raising=False)

    s = Settings.from_env()
    assert s.phase0_cache_ttl_seconds == 3600
    assert s.yahoo_timeout_seconds == 15
    assert s.news_timeout_seconds == 15
    assert s.news_max_articles == 5
    assert s.phase0_cache_dir == Path(".cache/foliotracker/phase0")
    assert s.source_cache_dir == Path(".cache/foliotracker/sources")
    assert s.yahoo_source_ttl_seconds == 3600
    assert s.news_source_ttl_seconds == 900
    assert s.sec_source_ttl_seconds == 3600


def test_settings_phase0_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHASE0_CACHE_TTL_SECONDS", "120")
    monkeypatch.setenv("PHASE0_CACHE_DIR", "/tmp/ft-cache")
    monkeypatch.setenv("YAHOO_TIMEOUT_SECONDS", "15")
    monkeypatch.setenv("NEWS_TIMEOUT_SECONDS", "8")
    monkeypatch.setenv("NEWS_MAX_ARTICLES", "3")
    s = Settings.from_env()
    assert s.phase0_cache_ttl_seconds == 120
    assert s.phase0_cache_dir == Path("/tmp/ft-cache")
    assert s.yahoo_timeout_seconds == 15
    assert s.news_timeout_seconds == 8
    assert s.news_max_articles == 3

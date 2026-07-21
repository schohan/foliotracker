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
        "YAHOO_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(key, raising=False)

    s = Settings.from_env()
    assert s.phase0_cache_ttl_seconds == 3600
    assert s.yahoo_timeout_seconds == 15
    assert s.phase0_cache_dir == Path(".cache/foliotracker/phase0")


def test_settings_phase0_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHASE0_CACHE_TTL_SECONDS", "120")
    monkeypatch.setenv("PHASE0_CACHE_DIR", "/tmp/ft-cache")
    monkeypatch.setenv("YAHOO_TIMEOUT_SECONDS", "15")
    s = Settings.from_env()
    assert s.phase0_cache_ttl_seconds == 120
    assert s.phase0_cache_dir == Path("/tmp/ft-cache")
    assert s.yahoo_timeout_seconds == 15

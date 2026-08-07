"""DataSource registry (Phase 2C.1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.configs.settings import Settings
from app.services.source_registry import (
    SOURCE_ALPHA_VANTAGE,
    SOURCE_GOOGLE_NEWS,
    SOURCE_SEC_EDGAR,
    SOURCE_SEC_XBRL,
    SOURCE_YAHOO,
    UnknownSourceError,
    build_registry,
    get_source,
    list_source_ids,
)


def _settings(**kwargs) -> Settings:
    base = dict(
        google_api_key=None,
        source_cache_dir=Path("/tmp/ft-sources"),
        yahoo_source_ttl_seconds=3600,
        news_source_ttl_seconds=900,
        sec_source_ttl_seconds=1800,
        yahoo_rate_limit_calls=10,
        news_rate_limit_calls=20,
        sec_rate_limit_calls=5,
    )
    base.update(kwargs)
    return Settings(**base)


def test_build_registry_has_live_sources() -> None:
    reg = build_registry(_settings())
    assert set(reg) == {
        SOURCE_YAHOO,
        SOURCE_GOOGLE_NEWS,
        SOURCE_SEC_EDGAR,
        SOURCE_SEC_XBRL,
        SOURCE_ALPHA_VANTAGE,
    }
    assert reg[SOURCE_YAHOO].confidence == 0.95
    assert reg[SOURCE_GOOGLE_NEWS].ttl_seconds == 900
    assert reg[SOURCE_SEC_EDGAR].rate_limit_calls == 5
    assert reg[SOURCE_SEC_XBRL].confidence == 0.95
    assert reg[SOURCE_ALPHA_VANTAGE].enabled is False
    assert reg[SOURCE_ALPHA_VANTAGE].confidence == 0.85


def test_alpha_vantage_enabled_when_api_key_set() -> None:
    reg = build_registry(_settings(alpha_vantage_api_key="demo-key"))
    assert reg[SOURCE_ALPHA_VANTAGE].enabled is True


def test_alpha_vantage_min_interval_defaults_to_window_over_calls() -> None:
    reg = build_registry(
        _settings(
            alpha_vantage_api_key="demo-key",
            alpha_vantage_rate_limit_calls=25,
            alpha_vantage_rate_limit_window_seconds=86400,
        )
    )
    assert reg[SOURCE_ALPHA_VANTAGE].rate_limit_min_interval_seconds == 86400 / 25


def test_alpha_vantage_min_interval_env_override() -> None:
    reg = build_registry(
        _settings(
            alpha_vantage_api_key="demo-key",
            alpha_vantage_min_interval_seconds=12.0,
            alpha_vantage_rate_limit_calls=25,
            alpha_vantage_rate_limit_window_seconds=86400,
        )
    )
    assert reg[SOURCE_ALPHA_VANTAGE].rate_limit_min_interval_seconds == 12.0


def test_get_source_and_list() -> None:
    s = _settings()
    assert get_source(SOURCE_YAHOO, s).source_id == SOURCE_YAHOO
    assert list_source_ids(s) == sorted(
        [
            SOURCE_YAHOO,
            SOURCE_GOOGLE_NEWS,
            SOURCE_SEC_EDGAR,
            SOURCE_SEC_XBRL,
            SOURCE_ALPHA_VANTAGE,
        ]
    )


def test_unknown_source() -> None:
    with pytest.raises(UnknownSourceError):
        get_source("not_a_source", _settings())

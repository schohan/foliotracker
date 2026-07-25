"""DataSource registry (Phase 2C.1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.configs.settings import Settings
from app.services.source_registry import (
    SOURCE_GOOGLE_NEWS,
    SOURCE_SEC_EDGAR,
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
    assert set(reg) == {SOURCE_YAHOO, SOURCE_GOOGLE_NEWS, SOURCE_SEC_EDGAR}
    assert reg[SOURCE_YAHOO].confidence == 0.95
    assert reg[SOURCE_GOOGLE_NEWS].ttl_seconds == 900
    assert reg[SOURCE_SEC_EDGAR].rate_limit_calls == 5


def test_get_source_and_list() -> None:
    s = _settings()
    assert get_source(SOURCE_YAHOO, s).source_id == SOURCE_YAHOO
    assert list_source_ids(s) == sorted(
        [SOURCE_YAHOO, SOURCE_GOOGLE_NEWS, SOURCE_SEC_EDGAR]
    )


def test_unknown_source() -> None:
    with pytest.raises(UnknownSourceError):
        get_source("not_a_source", _settings())

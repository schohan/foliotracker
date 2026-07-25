"""cached_fetch orchestration (Phase 2C.1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.configs.settings import Settings
from app.schemas.financials import FinancialMetrics
from app.services.source_cache import source_cache_store
from app.services.source_fetch import (
    SourceRateLimitedError,
    cached_fetch,
)
from app.services.source_registry import SOURCE_YAHOO


def _settings(tmp_path: Path, **kwargs) -> Settings:
    base = dict(
        google_api_key=None,
        source_cache_dir=tmp_path,
        yahoo_source_ttl_seconds=3600,
        yahoo_rate_limit_calls=100,
        source_rate_limit_window_seconds=3600,
    )
    base.update(kwargs)
    return Settings(**base)


def test_cached_fetch_live_then_hit(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    calls = {"n": 0}

    def fetch() -> FinancialMetrics:
        calls["n"] += 1
        return FinancialMetrics(ticker="NVDA", pe_ratio=40.0)

    first = cached_fetch(
        SOURCE_YAHOO,
        "NVDA",
        fetch,
        FinancialMetrics,
        app_settings=s,
    )
    assert first.meta.cache_hit is False
    assert first.data.pe_ratio == 40.0
    assert calls["n"] == 1

    second = cached_fetch(
        SOURCE_YAHOO,
        "NVDA",
        fetch,
        FinancialMetrics,
        app_settings=s,
    )
    assert second.meta.cache_hit is True
    assert calls["n"] == 1


def test_cached_fetch_rate_limited_uses_stale(tmp_path: Path) -> None:
    s = _settings(tmp_path, yahoo_rate_limit_calls=1)
    source_cache_store(
        SOURCE_YAHOO,
        "NVDA",
        FinancialMetrics(ticker="NVDA", pe_ratio=11.0).model_dump(mode="json"),
        app_settings=s,
    )
    # Expire the entry by using ttl=0 for lookup path: store then force rate limit
    # Consume the only budget slot with a live fetch that overwrites
    cached_fetch(
        SOURCE_YAHOO,
        "AAPL",
        lambda: FinancialMetrics(ticker="AAPL", pe_ratio=1.0),
        FinancialMetrics,
        app_settings=s,
    )

    # Backdate NVDA so it is stale, budget already used by AAPL
    import json
    from datetime import datetime, timedelta, timezone

    path = tmp_path / "yahoo" / "NVDA.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["fetched_at"] = (
        datetime.now(timezone.utc) - timedelta(hours=5)
    ).isoformat()
    path.write_text(json.dumps(data), encoding="utf-8")

    calls = {"n": 0}

    def fetch() -> FinancialMetrics:
        calls["n"] += 1
        return FinancialMetrics(ticker="NVDA", pe_ratio=99.0)

    result = cached_fetch(
        SOURCE_YAHOO,
        "NVDA",
        fetch,
        FinancialMetrics,
        app_settings=s,
    )
    assert result.meta.rate_limited is True
    assert result.meta.stale is True
    assert result.data.pe_ratio == 11.0
    assert calls["n"] == 0


def test_cached_fetch_rate_limited_no_stale_raises(tmp_path: Path) -> None:
    s = _settings(tmp_path, yahoo_rate_limit_calls=1)
    cached_fetch(
        SOURCE_YAHOO,
        "AAPL",
        lambda: FinancialMetrics(ticker="AAPL"),
        FinancialMetrics,
        app_settings=s,
    )

    with pytest.raises(SourceRateLimitedError):
        cached_fetch(
            SOURCE_YAHOO,
            "NVDA",
            lambda: FinancialMetrics(ticker="NVDA"),
            FinancialMetrics,
            app_settings=s,
        )

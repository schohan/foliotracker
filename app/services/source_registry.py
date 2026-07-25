"""DataSource registry — config-driven source ids for Phase 2C."""

from __future__ import annotations

from app.configs.settings import Settings, settings as default_settings
from app.schemas.sources import DataSourceConfig

SOURCE_YAHOO = "yahoo"
SOURCE_GOOGLE_NEWS = "google_news"
SOURCE_SEC_EDGAR = "sec_edgar"
SOURCE_SEC_XBRL = "sec_xbrl"

# Planned (not registered as live until implemented):
# SOURCE_ALPHA_VANTAGE = "alpha_vantage"


class UnknownSourceError(KeyError):
    """source_id is not in the registry."""


def build_registry(app_settings: Settings | None = None) -> dict[str, DataSourceConfig]:
    """Build the live source registry from settings."""
    s = app_settings if app_settings is not None else default_settings
    return {
        SOURCE_YAHOO: DataSourceConfig(
            source_id=SOURCE_YAHOO,
            confidence=0.95,
            ttl_seconds=s.yahoo_source_ttl_seconds,
            rate_limit_calls=s.yahoo_rate_limit_calls,
            rate_limit_window_seconds=s.source_rate_limit_window_seconds,
            timeout_seconds=s.yahoo_timeout_seconds,
            enabled=True,
        ),
        SOURCE_GOOGLE_NEWS: DataSourceConfig(
            source_id=SOURCE_GOOGLE_NEWS,
            confidence=0.7,
            ttl_seconds=s.news_source_ttl_seconds,
            rate_limit_calls=s.news_rate_limit_calls,
            rate_limit_window_seconds=s.source_rate_limit_window_seconds,
            timeout_seconds=s.news_timeout_seconds,
            enabled=True,
        ),
        SOURCE_SEC_EDGAR: DataSourceConfig(
            source_id=SOURCE_SEC_EDGAR,
            confidence=0.9,
            ttl_seconds=s.sec_source_ttl_seconds,
            rate_limit_calls=s.sec_rate_limit_calls,
            rate_limit_window_seconds=s.source_rate_limit_window_seconds,
            timeout_seconds=s.sec_timeout_seconds,
            enabled=True,
        ),
        SOURCE_SEC_XBRL: DataSourceConfig(
            source_id=SOURCE_SEC_XBRL,
            confidence=0.95,
            ttl_seconds=s.sec_xbrl_source_ttl_seconds,
            rate_limit_calls=s.sec_xbrl_rate_limit_calls,
            rate_limit_window_seconds=s.source_rate_limit_window_seconds,
            timeout_seconds=s.sec_xbrl_timeout_seconds,
            enabled=True,
        ),
    }


def get_source(
    source_id: str,
    app_settings: Settings | None = None,
) -> DataSourceConfig:
    """Return config for ``source_id`` or raise UnknownSourceError."""
    registry = build_registry(app_settings)
    try:
        return registry[source_id]
    except KeyError as exc:
        raise UnknownSourceError(source_id) from exc


def list_source_ids(app_settings: Settings | None = None) -> list[str]:
    return sorted(build_registry(app_settings).keys())

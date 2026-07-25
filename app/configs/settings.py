"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    google_api_key: str | None = None
    default_model: str = "gemini-2.0-flash"
    mongo_uri: str | None = None
    phase0_cache_ttl_seconds: int = 3600
    phase0_cache_dir: Path = Path(".cache/foliotracker/phase0")
    # Phase 2C.1 — per-source cache + soft local rate budgets
    source_cache_dir: Path = Path(".cache/foliotracker/sources")
    yahoo_source_ttl_seconds: int = 3600
    news_source_ttl_seconds: int = 900
    sec_source_ttl_seconds: int = 3600
    sec_xbrl_source_ttl_seconds: int = 86400
    source_rate_limit_window_seconds: int = 3600
    yahoo_rate_limit_calls: int = 100
    news_rate_limit_calls: int = 100
    sec_rate_limit_calls: int = 30
    sec_xbrl_rate_limit_calls: int = 20
    yahoo_timeout_seconds: int = 15
    news_timeout_seconds: int = 15
    news_max_articles: int = 5
    sec_timeout_seconds: int = 15
    sec_xbrl_timeout_seconds: int = 30
    sec_max_filings: int = 5
    sec_user_agent: str = "FolioTracker contact@example.com"
    # Phase 2C — Alpha Vantage fill-gaps (optional; disabled without API key)
    alpha_vantage_api_key: str | None = None
    alpha_vantage_source_ttl_seconds: int = 86400
    alpha_vantage_rate_limit_calls: int = 25
    alpha_vantage_rate_limit_window_seconds: int = 86400
    alpha_vantage_timeout_seconds: int = 20
    # Watchlist dashboard (local JSON)
    watchlist_path: Path = Path(".cache/foliotracker/watchlist.json")
    watchlist_cors_origins: str = "http://localhost:5173"

    @classmethod
    def from_env(cls) -> Settings:
        cache_dir = os.getenv(
            "PHASE0_CACHE_DIR",
            os.getenv("CACHE_DIR", ".cache/foliotracker/phase0"),
        )
        ttl = os.getenv(
            "PHASE0_CACHE_TTL_SECONDS",
            os.getenv("CACHE_TTL_SECONDS", "3600"),
        )
        source_cache_dir = os.getenv(
            "SOURCE_CACHE_DIR",
            ".cache/foliotracker/sources",
        )
        return cls(
            google_api_key=os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"),
            default_model=os.getenv("FOLIOTRACKER_MODEL", "gemini-2.0-flash"),
            mongo_uri=os.getenv("MONGO_URI"),
            phase0_cache_ttl_seconds=int(ttl),
            phase0_cache_dir=Path(cache_dir),
            source_cache_dir=Path(source_cache_dir),
            yahoo_source_ttl_seconds=int(
                os.getenv("YAHOO_SOURCE_TTL_SECONDS", "3600")
            ),
            news_source_ttl_seconds=int(
                os.getenv("NEWS_SOURCE_TTL_SECONDS", "900")
            ),
            sec_source_ttl_seconds=int(
                os.getenv("SEC_SOURCE_TTL_SECONDS", "3600")
            ),
            sec_xbrl_source_ttl_seconds=int(
                os.getenv("SEC_XBRL_SOURCE_TTL_SECONDS", "86400")
            ),
            source_rate_limit_window_seconds=int(
                os.getenv("SOURCE_RATE_LIMIT_WINDOW_SECONDS", "3600")
            ),
            yahoo_rate_limit_calls=int(
                os.getenv("YAHOO_RATE_LIMIT_CALLS", "100")
            ),
            news_rate_limit_calls=int(os.getenv("NEWS_RATE_LIMIT_CALLS", "100")),
            sec_rate_limit_calls=int(os.getenv("SEC_RATE_LIMIT_CALLS", "30")),
            sec_xbrl_rate_limit_calls=int(
                os.getenv("SEC_XBRL_RATE_LIMIT_CALLS", "20")
            ),
            yahoo_timeout_seconds=int(os.getenv("YAHOO_TIMEOUT_SECONDS", "15")),
            news_timeout_seconds=int(os.getenv("NEWS_TIMEOUT_SECONDS", "15")),
            news_max_articles=int(os.getenv("NEWS_MAX_ARTICLES", "5")),
            sec_timeout_seconds=int(os.getenv("SEC_TIMEOUT_SECONDS", "15")),
            sec_xbrl_timeout_seconds=int(
                os.getenv("SEC_XBRL_TIMEOUT_SECONDS", "30")
            ),
            sec_max_filings=int(os.getenv("SEC_MAX_FILINGS", "5")),
            sec_user_agent=os.getenv(
                "SEC_USER_AGENT",
                "FolioTracker contact@example.com",
            ),
            alpha_vantage_api_key=os.getenv("ALPHA_VANTAGE_API_KEY") or None,
            alpha_vantage_source_ttl_seconds=int(
                os.getenv("ALPHA_VANTAGE_SOURCE_TTL_SECONDS", "86400")
            ),
            alpha_vantage_rate_limit_calls=int(
                os.getenv("ALPHA_VANTAGE_RATE_LIMIT_CALLS", "25")
            ),
            alpha_vantage_rate_limit_window_seconds=int(
                os.getenv("ALPHA_VANTAGE_RATE_LIMIT_WINDOW_SECONDS", "86400")
            ),
            alpha_vantage_timeout_seconds=int(
                os.getenv("ALPHA_VANTAGE_TIMEOUT_SECONDS", "20")
            ),
            watchlist_path=Path(
                os.getenv(
                    "WATCHLIST_PATH",
                    ".cache/foliotracker/watchlist.json",
                )
            ),
            watchlist_cors_origins=os.getenv(
                "WATCHLIST_CORS_ORIGINS",
                "http://localhost:5173",
            ),
        )


settings = Settings.from_env()

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
    yahoo_timeout_seconds: int = 15

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
        return cls(
            google_api_key=os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"),
            default_model=os.getenv("FOLIOTRACKER_MODEL", "gemini-2.0-flash"),
            mongo_uri=os.getenv("MONGO_URI"),
            phase0_cache_ttl_seconds=int(ttl),
            phase0_cache_dir=Path(cache_dir),
            yahoo_timeout_seconds=int(os.getenv("YAHOO_TIMEOUT_SECONDS", "15")),
        )


settings = Settings.from_env()

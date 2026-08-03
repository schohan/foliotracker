"""Brief ring store + miss log."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.configs.settings import Settings
from app.schemas.brief import BriefGenerationStatus, DailyBrief
from app.services import brief_store as store


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        watchlist_path=tmp_path / "w.json",
        source_cache_dir=tmp_path / "sources",
        phase0_cache_dir=tmp_path / "phase0",
        brief_store_path=tmp_path / "briefs.json",
        brief_miss_log_path=tmp_path / "misses.jsonl",
        brief_ring_size=3,
    )


def test_ring_keeps_newest(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    for i in range(5):
        store.save_brief(
            DailyBrief(
                generated_at=datetime(2024, 1, i + 1, tzinfo=timezone.utc),
                universe_count=i,
                generation_status=BriefGenerationStatus.COMPLETE,
            ),
            app_settings=s,
            ring_size=3,
        )
    briefs = store.list_briefs(app_settings=s)
    assert len(briefs) == 3
    assert briefs[0].universe_count == 4
    latest = store.get_latest_brief(app_settings=s)
    assert latest is not None
    assert latest.universe_count == 4


def test_miss_log_append(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    entry = store.append_miss_note("Missed FDA news on XYZ", app_settings=s)
    assert "FDA" in entry["note"]
    text = Path(s.brief_miss_log_path).read_text(encoding="utf-8")
    assert "Missed FDA" in text

"""Thesis dashboard ring + per-ticker snapshot rings."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.configs.settings import Settings
from app.schemas.thesis import (
    ThesisChange,
    ThesisDashboard,
    ThesisSignalVector,
    ThesisSnapshot,
    ThesisVerdict,
)
from app.services import thesis_store


def _settings(tmp_path: Path) -> Settings:
    return Settings(thesis_store_path=tmp_path / "thesis.json")


def _dashboard(universe: int) -> ThesisDashboard:
    return ThesisDashboard(
        generated_at=datetime(2026, 8, 7, tzinfo=timezone.utc),
        universe_count=universe,
    )


def _snap(ticker: str, day: int) -> ThesisSnapshot:
    as_of = datetime(2026, 8, day, tzinfo=timezone.utc)
    return ThesisSnapshot(
        ticker=ticker,
        as_of=as_of,
        original_thesis="Cloud spending accelerating.",
        signals=ThesisSignalVector(graham_score=70.0),
        change=ThesisChange(
            verdict=ThesisVerdict.NO_CHANGE,
            as_of=as_of,
            evidence=["baseline — no prior quarter"],
        ),
    )


def test_latest_none_when_empty(tmp_path: Path) -> None:
    assert thesis_store.get_latest_dashboard(_settings(tmp_path)) is None


def test_save_and_get_latest(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    thesis_store.save_dashboard(_dashboard(1), app_settings=s)
    thesis_store.save_dashboard(_dashboard(2), app_settings=s)
    latest = thesis_store.get_latest_dashboard(s)
    assert latest is not None
    assert latest.universe_count == 2


def test_ring_caps_entries(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    for i in range(5):
        thesis_store.save_dashboard(_dashboard(i), app_settings=s, ring_size=3)
    doc = thesis_store.load_raw(s)
    assert len(doc["dashboards"]) == 3
    assert doc["dashboards"][0]["universe_count"] == 4


def test_corrupt_file_returns_default(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    Path(s.thesis_store_path).parent.mkdir(parents=True, exist_ok=True)
    Path(s.thesis_store_path).write_text("not json", encoding="utf-8")
    assert thesis_store.get_latest_dashboard(s) is None


def test_snapshot_ring_per_ticker(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    thesis_store.append_snapshot(_snap("NVDA", 1), app_settings=s, ring_size=3)
    thesis_store.append_snapshot(_snap("NVDA", 2), app_settings=s, ring_size=3)
    thesis_store.append_snapshot(_snap("AAPL", 1), app_settings=s, ring_size=3)
    nvda = thesis_store.get_snapshots("NVDA", app_settings=s)
    assert len(nvda) == 2
    assert nvda[0].as_of.day == 2
    assert thesis_store.get_latest_snapshot("NVDA", app_settings=s).as_of.day == 2
    assert len(thesis_store.get_snapshots("AAPL", app_settings=s)) == 1


def test_snapshot_ring_caps(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    for day in range(1, 6):
        thesis_store.append_snapshot(_snap("NVDA", day), app_settings=s, ring_size=3)
    snaps = thesis_store.get_snapshots("NVDA", app_settings=s)
    assert len(snaps) == 3
    assert snaps[0].as_of.day == 5


def test_dashboard_save_preserves_snapshots(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    thesis_store.append_snapshot(_snap("NVDA", 1), app_settings=s)
    thesis_store.save_dashboard(_dashboard(1), app_settings=s)
    assert thesis_store.get_latest_snapshot("NVDA", app_settings=s) is not None
    doc = thesis_store.load_raw(s)
    assert "snapshots" in doc and "NVDA" in doc["snapshots"]

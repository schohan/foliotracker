"""Thesis HTTP API."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.configs.settings import Settings
from app.schemas.phase0 import Phase0Result, Phase0Status
from app.schemas.thesis import ThesisDashboard
from app.services import thesis_store, watchlist_store as store


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        watchlist_path=tmp_path / "w.json",
        source_cache_dir=tmp_path / "sources",
        phase0_cache_dir=tmp_path / "phase0",
        thesis_store_path=tmp_path / "thesis.json",
        watchlist_cors_origins="http://localhost:5173",
    )


def _client(s: Settings, thesis_fn) -> TestClient:
    return TestClient(
        create_app(
            app_settings=s,
            research_fn=lambda *a, **k: Phase0Result(
                ticker="NVDA",
                status=Phase0Status.OK,
                request_id="t",
            ),
            thesis_generate_fn=thesis_fn,
        )
    )


def test_thesis_get_null_then_generate(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    store.put_membership(["NVDA"], [], s)

    def fake_generate(*, app_settings=None, force_refresh=False) -> ThesisDashboard:
        dash = ThesisDashboard(
            generated_at=datetime(2026, 8, 7, tzinfo=timezone.utc),
            universe_count=1,
            tickers_considered=1,
        )
        return thesis_store.save_dashboard(dash, app_settings=app_settings or s)

    client = _client(s, fake_generate)

    r = client.get("/api/thesis")
    assert r.status_code == 200
    assert r.json() is None

    r = client.post("/api/thesis/generate", json={"force_refresh": False})
    assert r.status_code == 200
    body = r.json()
    assert body["universe_count"] == 1
    assert body["disclaimer"]
    assert body["frameworks"] == ["graham", "financial_strength"]

    r = client.get("/api/thesis")
    assert r.status_code == 200
    assert r.json()["universe_count"] == 1


def test_thesis_generate_accepts_empty_body(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    store.put_membership([], [], s)

    calls: dict = {}

    def fake_generate(*, app_settings=None, force_refresh=False) -> ThesisDashboard:
        calls["force_refresh"] = force_refresh
        return ThesisDashboard(
            generated_at=datetime(2026, 8, 7, tzinfo=timezone.utc),
        )

    client = _client(s, fake_generate)
    r = client.post("/api/thesis/generate")
    assert r.status_code == 200
    assert calls["force_refresh"] is False

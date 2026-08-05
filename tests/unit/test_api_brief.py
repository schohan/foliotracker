"""Brief HTTP API."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.configs.settings import Settings
from app.schemas.brief import BriefGenerationStatus, DailyBrief
from app.schemas.phase0 import Phase0Result, Phase0Status
from app.services import brief_store, watchlist_store as store


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        watchlist_path=tmp_path / "w.json",
        source_cache_dir=tmp_path / "sources",
        phase0_cache_dir=tmp_path / "phase0",
        brief_store_path=tmp_path / "briefs.json",
        brief_miss_log_path=tmp_path / "misses.jsonl",
        watchlist_cors_origins="http://localhost:5173",
    )


def test_brief_get_null_then_generate_and_miss(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    store.put_membership(["NVDA"], [], s)

    def fake_generate(*, app_settings=None, force_refresh=False) -> DailyBrief:
        brief = DailyBrief(
            generated_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
            generation_status=BriefGenerationStatus.COMPLETE,
            universe_count=1,
            tickers_considered=1,
            tickers=[],
            empty_message="Nothing material in the last 24h.",
        )
        return brief_store.save_brief(brief, app_settings=app_settings or s)

    client = TestClient(
        create_app(
            app_settings=s,
            research_fn=lambda *a, **k: Phase0Result(
                ticker="NVDA",
                status=Phase0Status.OK,
                request_id="t",
            ),
            brief_generate_fn=fake_generate,
        )
    )

    r = client.get("/api/brief")
    assert r.status_code == 200
    assert r.json() is None

    r = client.post("/api/brief/generate", json={"force_refresh": False})
    assert r.status_code == 200
    body = r.json()
    assert body["universe_count"] == 1
    assert body["empty_message"]

    r = client.get("/api/brief")
    assert r.status_code == 200
    assert r.json()["universe_count"] == 1

    r = client.post("/api/brief/miss", json={"note": "Missed 8-K on NVDA"})
    assert r.status_code == 200
    assert "Missed 8-K" in r.json()["note"]
    assert Path(s.brief_miss_log_path).exists()

    r = client.get("/api/brief/history")
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = client.post(
        "/api/brief/explain",
        json={
            "ticker": "NVDA",
            "text": "Goldman upgrades",
            "category": "analyst_rating",
            "list_kind": "held",
        },
    )
    assert r.status_code == 200
    assert r.json()["explain_busy"]
    assert r.json()["provider"] in {"deterministic", "canned", "llm"}


def test_risk_still_works_after_brief_routes(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    store.put_membership([], ["AAPL"], s)
    client = TestClient(create_app(app_settings=s))
    r = client.get("/api/risk")
    assert r.status_code == 200
    assert r.json()["held_count"] == 0

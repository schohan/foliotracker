"""FastAPI watchlist routes with mocked Phase0."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.configs.settings import Settings
from app.schemas.evidence import Evidence, EvidenceBundle
from app.schemas.phase0 import Phase0Result, Phase0Status
from app.schemas.report import InvestmentThesis, Scorecard, ThesisClaim
from app.schemas.watchlist import ListKind


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        google_api_key=None,
        watchlist_path=tmp_path / "watchlist.json",
        watchlist_cors_origins="http://localhost:5173",
    )


def _ok_result(ticker: str) -> Phase0Result:
    return Phase0Result(
        ticker=ticker,
        status=Phase0Status.OK,
        evidence=EvidenceBundle(
            ticker=ticker,
            items=[
                Evidence(
                    id="ev1",
                    type="financial",
                    source="yahoo",
                    confidence=0.9,
                    data={},
                )
            ],
        ),
        thesis=InvestmentThesis(
            ticker=ticker,
            thesis=f"{ticker} thesis.",
            claims=[ThesisClaim(text="c", evidence_ids=["ev1"])],
        ),
        scorecard=Scorecard(ticker=ticker, growth_score=61.0, risk_score=33.0),
        cache_hit=True,
        request_id=f"api-{ticker}",
    )


def _client(tmp_path: Path) -> TestClient:
    app = create_app(
        app_settings=_settings(tmp_path),
        research_fn=lambda t, **k: _ok_result(t),
        intake_quote_checker=lambda _t: "ok",
    )
    return TestClient(app)


def test_health(tmp_path: Path) -> None:
    r = _client(tmp_path).get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_put_get_add_refresh(tmp_path: Path) -> None:
    client = _client(tmp_path)
    r = client.put(
        "/api/watchlist",
        json={"held": ["NVDA"], "watched": ["AAPL"]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["membership"]["held"] == ["NVDA"]
    assert body["membership"]["watched"] == ["AAPL"]
    assert "disclaimer" in body

    r = client.post(
        "/api/watchlist/tickers",
        json={"ticker": "msft", "list_kind": "watched"},
    )
    assert r.status_code == 200
    assert "MSFT" in r.json()["membership"]["watched"]

    r = client.post("/api/watchlist/NVDA/refresh")
    assert r.status_code == 200
    assert r.json()["growth_score"] == 61.0
    assert r.json()["cache_hit"] is True

    r = client.get("/api/watchlist")
    summaries = {row["ticker"]: row for row in r.json()["summaries"]}
    assert summaries["NVDA"]["growth_score"] == 61.0


def test_refresh_unknown_404(tmp_path: Path) -> None:
    client = _client(tmp_path)
    r = client.post("/api/watchlist/ZZZZ/refresh")
    assert r.status_code == 404


def test_batch_refresh_and_research(tmp_path: Path) -> None:
    client = _client(tmp_path)
    client.put("/api/watchlist", json={"held": ["NVDA"], "watched": ["AAPL"]})
    r = client.post("/api/watchlist/refresh", json={"max_tickers": 8})
    assert r.status_code == 200
    assert set(r.json()["refreshed"]) == {"NVDA", "AAPL"}

    r = client.get("/api/research/NVDA")
    assert r.status_code == 200
    assert r.json()["result"]["ticker"] == "NVDA"
    assert r.json()["list_kind"] == ListKind.HELD.value


def test_delete_ticker(tmp_path: Path) -> None:
    client = _client(tmp_path)
    client.put("/api/watchlist", json={"held": [], "watched": ["AAPL"]})
    r = client.delete("/api/watchlist/tickers/AAPL")
    assert r.status_code == 200
    assert r.json()["membership"]["watched"] == []


def test_intake_bulk_dedupe_no_research(tmp_path: Path) -> None:
    client = _client(tmp_path)
    client.put("/api/watchlist", json={"held": ["NVDA"], "watched": []})
    r = client.post(
        "/api/watchlist/intake",
        json={"text": "NVDA, AAPL, MSFT", "list_kind": "watched"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["added_count"] == 2
    assert body["skipped_duplicate_count"] == 1
    assert "NVDA" in body["skipped_duplicate"]
    assert set(body["added"]) == {"AAPL", "MSFT"}
    assert body["state"]["membership"]["held"] == ["NVDA"]
    assert set(body["state"]["membership"]["watched"]) == {"AAPL", "MSFT"}
    # Membership-only: summaries for new tickers have null research fields
    summaries = {row["ticker"]: row for row in body["state"]["summaries"]}
    assert summaries["AAPL"]["growth_score"] is None


def test_intake_empty_400(tmp_path: Path) -> None:
    client = _client(tmp_path)
    r = client.post(
        "/api/watchlist/intake",
        json={"text": "the stock market today", "list_kind": "held"},
    )
    assert r.status_code == 400


def test_bulk_move_and_remove(tmp_path: Path) -> None:
    client = _client(tmp_path)
    client.put(
        "/api/watchlist",
        json={"held": ["NVDA"], "watched": ["AAPL", "MSFT"]},
    )
    r = client.post(
        "/api/watchlist/bulk",
        json={"tickers": ["AAPL", "NVDA"], "action": "move_to_held"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["affected"] == ["AAPL"]
    assert body["skipped_noop"] == ["NVDA"]
    assert set(body["state"]["membership"]["held"]) == {"NVDA", "AAPL"}
    assert body["state"]["membership"]["watched"] == ["MSFT"]

    r = client.post(
        "/api/watchlist/bulk",
        json={"tickers": ["AAPL", "GONE"], "action": "remove"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["affected"] == ["AAPL"]
    assert body["skipped_not_found"] == ["GONE"]
    assert body["state"]["membership"]["held"] == ["NVDA"]
    assert body["state"]["membership"]["watched"] == ["MSFT"]


def test_bulk_empty_tickers_400(tmp_path: Path) -> None:
    client = _client(tmp_path)
    r = client.post(
        "/api/watchlist/bulk",
        json={"tickers": [], "action": "remove"},
    )
    assert r.status_code == 422


def test_bulk_invalid_ticker_400(tmp_path: Path) -> None:
    client = _client(tmp_path)
    client.put("/api/watchlist", json={"held": ["NVDA"], "watched": []})
    r = client.post(
        "/api/watchlist/bulk",
        json={"tickers": ["!!!"], "action": "remove"},
    )
    assert r.status_code == 400


def test_get_risk_empty_held(tmp_path: Path) -> None:
    client = _client(tmp_path)
    client.put("/api/watchlist", json={"held": [], "watched": ["AAPL"]})
    r = client.get("/api/risk")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["held_count"] == 0
    assert body["positions"] == []
    assert body["top_correlations"] == []
    assert body["correlation_pairs_known"] == 0
    assert "disclaimer" in body


def test_get_risk_held_partial_without_cache(tmp_path: Path) -> None:
    client = _client(tmp_path)
    client.put("/api/watchlist", json={"held": ["NVDA"], "watched": []})
    r = client.get("/api/risk")
    assert r.status_code == 200
    body = r.json()
    assert body["held_count"] == 1
    assert body["top_name_weight"] == 1.0
    assert body["status"] == "partial"
    assert body["equal_weight"] is True
    assert body["top_correlations"] == []
    assert body["correlation_pairs_known"] == 0

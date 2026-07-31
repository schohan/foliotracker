"""Portfolio Risk v1 — concentration from Held + cache/summaries."""

from __future__ import annotations

from pathlib import Path

from app.configs.settings import Settings
from app.schemas.financials import CompanyProfile, FinancialMetrics
from app.schemas.phase0 import Phase0Result, Phase0Status
from app.schemas.portfolio import PortfolioRiskSnapshot
from app.schemas.report import Scorecard
from app.schemas.watchlist import ListKind, WatchlistTickerSummary
from app.services import watchlist_store as store
from app.services.portfolio_risk_service import build_portfolio_risk


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        google_api_key=None,
        watchlist_path=tmp_path / "watchlist.json",
        phase0_cache_dir=tmp_path / "phase0",
        watchlist_cors_origins="http://localhost:5173",
    )


def _phase0(
    ticker: str,
    *,
    sector: str | None = None,
    risk_score: float | None = 40.0,
    status: Phase0Status = Phase0Status.OK,
) -> Phase0Result:
    profile = CompanyProfile(sector=sector) if sector is not None else None
    fundamentals = FinancialMetrics(
        ticker=ticker,
        profile=profile,
    )
    return Phase0Result(
        ticker=ticker,
        status=status,
        fundamentals=fundamentals,
        scorecard=Scorecard(ticker=ticker, risk_score=risk_score),
        request_id=f"risk-{ticker}",
    )


def test_empty_held_is_ok(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    store.put_membership([], ["AAPL"], s)
    snap = build_portfolio_risk(app_settings=s)
    assert snap.status == Phase0Status.OK
    assert snap.held_count == 0
    assert snap.positions == []
    assert snap.sector_buckets == []
    assert snap.top_name_weight is None
    assert snap.avg_risk_score is None
    assert snap.gaps == []
    assert "informational" in snap.disclaimer.lower()


def test_one_ticker_full_weight(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    store.put_membership(["NVDA"], [], s)
    store.upsert_summary(
        WatchlistTickerSummary(
            ticker="NVDA",
            list_kind=ListKind.HELD,
            status=Phase0Status.OK,
            risk_score=55.0,
        ),
        s,
    )
    cache = {"NVDA": _phase0("NVDA", sector="Technology", risk_score=55.0)}

    snap = build_portfolio_risk(
        app_settings=s,
        cache_lookup_fn=lambda t, **k: cache.get(t.upper()),
    )
    assert snap.status == Phase0Status.OK
    assert snap.held_count == 1
    assert snap.top_name_weight == 1.0
    assert len(snap.positions) == 1
    assert snap.positions[0].ticker == "NVDA"
    assert snap.positions[0].weight == 1.0
    assert snap.positions[0].sector == "Technology"
    assert snap.avg_risk_score == 55.0
    assert len(snap.sector_buckets) == 1
    assert snap.sector_buckets[0].sector == "Technology"
    assert snap.sector_buckets[0].weight == 1.0
    assert snap.sector_buckets[0].tickers == ["NVDA"]
    assert snap.gaps == []


def test_multi_sector_equal_weight(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    store.put_membership(["NVDA", "JPM", "XOM"], [], s)
    for t, risk in [("NVDA", 30.0), ("JPM", 45.0), ("XOM", 60.0)]:
        store.upsert_summary(
            WatchlistTickerSummary(
                ticker=t,
                list_kind=ListKind.HELD,
                status=Phase0Status.OK,
                risk_score=risk,
            ),
            s,
        )
    cache = {
        "NVDA": _phase0("NVDA", sector="Technology", risk_score=30.0),
        "JPM": _phase0("JPM", sector="Financial Services", risk_score=45.0),
        "XOM": _phase0("XOM", sector="Energy", risk_score=60.0),
    }
    snap = build_portfolio_risk(
        app_settings=s,
        cache_lookup_fn=lambda t, **k: cache.get(t.upper()),
    )
    assert snap.status == Phase0Status.OK
    assert snap.held_count == 3
    assert abs((snap.top_name_weight or 0) - 1 / 3) < 1e-9
    assert all(abs(p.weight - 1 / 3) < 1e-9 for p in snap.positions)
    by_sector = {b.sector: b for b in snap.sector_buckets}
    assert set(by_sector) == {"Technology", "Financial Services", "Energy"}
    for b in snap.sector_buckets:
        assert abs(b.weight - 1 / 3) < 1e-9
        assert b.count == 1
    assert abs((snap.avg_risk_score or 0) - 45.0) < 1e-9
    assert snap.risk_scores_known == 3


def test_missing_sector_is_partial(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    store.put_membership(["NVDA", "AAPL"], [], s)
    store.upsert_summary(
        WatchlistTickerSummary(
            ticker="NVDA",
            list_kind=ListKind.HELD,
            status=Phase0Status.OK,
            risk_score=40.0,
        ),
        s,
    )
    store.upsert_summary(
        WatchlistTickerSummary(
            ticker="AAPL",
            list_kind=ListKind.HELD,
            status=Phase0Status.OK,
            risk_score=35.0,
        ),
        s,
    )
    cache = {
        "NVDA": _phase0("NVDA", sector="Technology"),
        "AAPL": _phase0("AAPL", sector=None),
    }
    # Empty sector string on profile
    cache["AAPL"] = Phase0Result(
        ticker="AAPL",
        status=Phase0Status.OK,
        fundamentals=FinancialMetrics(
            ticker="AAPL",
            profile=CompanyProfile(sector=None),
        ),
        scorecard=Scorecard(ticker="AAPL", risk_score=35.0),
        request_id="risk-AAPL",
    )
    snap = build_portfolio_risk(
        app_settings=s,
        cache_lookup_fn=lambda t, **k: cache.get(t.upper()),
    )
    assert snap.status == Phase0Status.PARTIAL
    assert any("AAPL" in g and "sector" in g.lower() for g in snap.gaps)
    unknown = next(b for b in snap.sector_buckets if b.sector == "Unknown")
    assert "AAPL" in unknown.tickers
    assert abs(unknown.weight - 0.5) < 1e-9


def test_cache_miss_and_missing_risk_score_partial(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    store.put_membership(["ZZZ"], [], s)
    # No summary risk_score, no cache
    snap = build_portfolio_risk(
        app_settings=s,
        cache_lookup_fn=lambda t, **k: None,
    )
    assert snap.status == Phase0Status.PARTIAL
    assert snap.held_count == 1
    assert snap.positions[0].sector is None
    assert snap.positions[0].risk_score is None
    assert snap.avg_risk_score is None
    assert snap.risk_scores_known == 0
    assert any("sector" in g.lower() for g in snap.gaps)
    assert any("risk" in g.lower() for g in snap.gaps)


def test_watched_ignored(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    store.put_membership(["NVDA"], ["AAPL"], s)
    store.upsert_summary(
        WatchlistTickerSummary(
            ticker="NVDA",
            list_kind=ListKind.HELD,
            risk_score=50.0,
            status=Phase0Status.OK,
        ),
        s,
    )
    cache = {
        "NVDA": _phase0("NVDA", sector="Technology", risk_score=50.0),
        "AAPL": _phase0("AAPL", sector="Technology", risk_score=10.0),
    }
    snap = build_portfolio_risk(
        app_settings=s,
        cache_lookup_fn=lambda t, **k: cache.get(t.upper()),
    )
    assert snap.held_count == 1
    assert [p.ticker for p in snap.positions] == ["NVDA"]


def test_snapshot_schema_roundtrip() -> None:
    snap = PortfolioRiskSnapshot(
        status=Phase0Status.OK,
        held_count=0,
    )
    assert PortfolioRiskSnapshot.model_validate(snap.model_dump()).held_count == 0

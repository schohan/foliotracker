"""Portfolio Risk — concentration + pairwise correlation from Held + caches."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from app.configs.settings import Settings
from app.schemas.financials import CompanyProfile, FinancialMetrics
from app.schemas.phase0 import Phase0Result, Phase0Status
from app.schemas.portfolio import PairCorrelation, PortfolioRiskSnapshot
from app.schemas.report import Scorecard
from app.schemas.watchlist import ListKind, WatchlistTickerSummary
from app.services import watchlist_store as store
from app.services.portfolio_risk_service import (
    MIN_OVERLAP_DAYS,
    build_portfolio_risk,
    compute_top_correlations,
)


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        google_api_key=None,
        watchlist_path=tmp_path / "watchlist.json",
        phase0_cache_dir=tmp_path / "phase0",
        source_cache_dir=tmp_path / "sources",
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


def _synth_closes(
    n: int = 80,
    *,
    start: float = 100.0,
    drift: float = 0.001,
    noise_amp: float = 0.0,
    seed: int = 0,
) -> list[tuple[str, float]]:
    """Synthetic daily closes long enough for MIN_OVERLAP_DAYS returns."""
    day0 = date(2024, 1, 2)
    px = start
    out: list[tuple[str, float]] = []
    for i in range(n):
        # Deterministic pseudo-noise from seed+i (no random module).
        noise = noise_amp * (((seed * 17 + i * 31) % 100) / 100.0 - 0.5)
        px = px * (1.0 + drift + noise)
        out.append(((day0 + timedelta(days=i)).isoformat(), px))
    return out


def _perfect_corr_histories() -> dict[str, list[tuple[str, float]]]:
    """Two series with identical returns → correlation ≈ 1."""
    base = _synth_closes(90, drift=0.002, noise_amp=0.01, seed=1)
    twin = [(d, px * 2.0) for d, px in base]
    return {"AAA": base, "BBB": twin}


def _no_history(_: str) -> None:
    return None


def test_empty_held_is_ok(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    store.put_membership([], ["AAPL"], s)
    snap = build_portfolio_risk(app_settings=s)
    assert snap.status == Phase0Status.OK
    assert snap.held_count == 0
    assert snap.positions == []
    assert snap.sector_buckets == []
    assert snap.top_correlations == []
    assert snap.correlation_pairs_known == 0
    assert snap.top_name_weight is None
    assert snap.avg_risk_score is None
    assert snap.gaps == []
    assert "informational" in snap.disclaimer.lower()


def test_one_ticker_full_weight_no_correlation_pairs(tmp_path: Path) -> None:
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
        history_lookup_fn=_no_history,
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
    assert snap.top_correlations == []
    assert snap.correlation_pairs_known == 0
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
    # Shared synthetic history so concentration stays status=ok.
    shared = _synth_closes(90, drift=0.001, noise_amp=0.02, seed=3)
    hist = {
        "NVDA": shared,
        "JPM": [(d, px * 1.1) for d, px in shared],
        "XOM": [(d, px * 0.9) for d, px in shared],
    }
    snap = build_portfolio_risk(
        app_settings=s,
        cache_lookup_fn=lambda t, **k: cache.get(t.upper()),
        history_lookup_fn=lambda t: hist.get(t.upper()),
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
    assert snap.correlation_pairs_known == 3
    assert len(snap.top_correlations) == 3


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
        "AAPL": Phase0Result(
            ticker="AAPL",
            status=Phase0Status.OK,
            fundamentals=FinancialMetrics(
                ticker="AAPL",
                profile=CompanyProfile(sector=None),
            ),
            scorecard=Scorecard(ticker="AAPL", risk_score=35.0),
            request_id="risk-AAPL",
        ),
    }
    shared = _synth_closes(90, seed=4)
    hist = {"NVDA": shared, "AAPL": [(d, px * 1.5) for d, px in shared]}
    snap = build_portfolio_risk(
        app_settings=s,
        cache_lookup_fn=lambda t, **k: cache.get(t.upper()),
        history_lookup_fn=lambda t: hist.get(t.upper()),
    )
    assert snap.status == Phase0Status.PARTIAL
    assert any("AAPL" in g and "sector" in g.lower() for g in snap.gaps)
    unknown = next(b for b in snap.sector_buckets if b.sector == "Unknown")
    assert "AAPL" in unknown.tickers
    assert abs(unknown.weight - 0.5) < 1e-9


def test_cache_miss_and_missing_risk_score_partial(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    store.put_membership(["ZZZ"], [], s)
    # No summary risk_score, no cache; single ticker → no correlation gaps
    snap = build_portfolio_risk(
        app_settings=s,
        cache_lookup_fn=lambda t, **k: None,
        history_lookup_fn=_no_history,
    )
    assert snap.status == Phase0Status.PARTIAL
    assert snap.held_count == 1
    assert snap.positions[0].sector is None
    assert snap.positions[0].risk_score is None
    assert snap.avg_risk_score is None
    assert snap.risk_scores_known == 0
    assert any("sector" in g.lower() for g in snap.gaps)
    assert any("risk" in g.lower() for g in snap.gaps)
    assert snap.top_correlations == []


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
        history_lookup_fn=_no_history,
    )
    assert snap.held_count == 1
    assert [p.ticker for p in snap.positions] == ["NVDA"]


def test_snapshot_schema_roundtrip() -> None:
    snap = PortfolioRiskSnapshot(
        status=Phase0Status.OK,
        held_count=0,
        top_correlations=[
            PairCorrelation(
                ticker_a="A",
                ticker_b="B",
                correlation=0.5,
                overlap_days=80,
            )
        ],
        correlation_pairs_known=1,
    )
    again = PortfolioRiskSnapshot.model_validate(snap.model_dump())
    assert again.held_count == 0
    assert again.top_correlations[0].correlation == 0.5


def test_two_tickers_high_correlation(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    store.put_membership(["AAA", "BBB"], [], s)
    for t in ("AAA", "BBB"):
        store.upsert_summary(
            WatchlistTickerSummary(
                ticker=t,
                list_kind=ListKind.HELD,
                status=Phase0Status.OK,
                risk_score=40.0,
            ),
            s,
        )
    cache = {
        "AAA": _phase0("AAA", sector="Technology"),
        "BBB": _phase0("BBB", sector="Technology"),
    }
    hist = _perfect_corr_histories()
    snap = build_portfolio_risk(
        app_settings=s,
        cache_lookup_fn=lambda t, **k: cache.get(t.upper()),
        history_lookup_fn=lambda t: hist.get(t.upper()),
    )
    assert snap.status == Phase0Status.OK
    assert snap.correlation_pairs_known == 1
    pair = snap.top_correlations[0]
    assert pair.ticker_a == "AAA"
    assert pair.ticker_b == "BBB"
    assert pair.overlap_days >= MIN_OVERLAP_DAYS
    assert pair.correlation > 0.99
    assert pair.window == "~1y daily returns"


def test_missing_history_partial(tmp_path: Path) -> None:
    s = _settings(tmp_path)
    store.put_membership(["AAA", "BBB"], [], s)
    for t in ("AAA", "BBB"):
        store.upsert_summary(
            WatchlistTickerSummary(
                ticker=t,
                list_kind=ListKind.HELD,
                status=Phase0Status.OK,
                risk_score=40.0,
            ),
            s,
        )
    cache = {
        "AAA": _phase0("AAA", sector="Technology"),
        "BBB": _phase0("BBB", sector="Technology"),
    }
    snap = build_portfolio_risk(
        app_settings=s,
        cache_lookup_fn=lambda t, **k: cache.get(t.upper()),
        history_lookup_fn=_no_history,
    )
    assert snap.status == Phase0Status.PARTIAL
    assert snap.top_correlations == []
    assert any("AAA" in g and "history" in g.lower() for g in snap.gaps)
    assert any("BBB" in g and "history" in g.lower() for g in snap.gaps)
    assert any("insufficient overlapping" in g.lower() for g in snap.gaps)


def test_insufficient_overlap_skipped() -> None:
    short = _synth_closes(10, seed=9)  # << MIN_OVERLAP_DAYS returns
    hist = {"AAA": short, "BBB": [(d, px * 2) for d, px in short]}
    top, gaps = compute_top_correlations(["AAA", "BBB"], hist)
    assert top == []
    assert any("insufficient overlapping" in g.lower() for g in gaps)


def test_top_correlations_sorted_by_abs() -> None:
    # A≈B high corr (scale); C = inverted daily moves → strongly negative vs A.
    base = _synth_closes(100, drift=0.001, noise_amp=0.02, seed=0)
    high = [(d, px * 1.2) for d, px in base]
    inv: list[tuple[str, float]] = []
    px = 100.0
    for i, (d, _) in enumerate(base):
        if i == 0:
            inv.append((d, px))
            continue
        prev_base = base[i - 1][1]
        cur_base = base[i][1]
        ret = (cur_base - prev_base) / prev_base
        px = px * (1.0 - ret)
        inv.append((d, px))
    hist = {"A": base, "B": high, "C": inv}
    top, gaps = compute_top_correlations(["A", "B", "C"], hist)
    assert gaps == []
    assert len(top) == 3
    abs_vals = [abs(p.correlation) for p in top]
    assert abs_vals == sorted(abs_vals, reverse=True)
    assert top[0].ticker_a == "A" and top[0].ticker_b == "B"
    assert top[0].correlation > 0.99
    assert top[-1].correlation < -0.99

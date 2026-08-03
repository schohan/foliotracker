"""Portfolio Risk — equal-weight concentration + pairwise correlation (Held).

Pure calculation over membership + cached Phase0 / Yahoo source history.
Never invents sector, scores, or correlations; gaps surface as ``partial``.
"""

from __future__ import annotations

import logging
import math
from collections import defaultdict
from typing import Callable

from app.configs.settings import Settings, settings as default_settings
from app.schemas.phase0 import PHASE0_DISCLAIMER, Phase0Result, Phase0Status
from app.schemas.portfolio import (
    HeldPositionRisk,
    PairCorrelation,
    PortfolioRiskSnapshot,
    SectorBucket,
)
from app.services import watchlist_store as store
from app.services.phase0_cache import cache_lookup
from app.services.yahoo_history import daily_returns, lookup_history_closes

logger = logging.getLogger(__name__)

CacheLookupFn = Callable[..., Phase0Result | None]
# Returns ordered (date_iso, close) pairs, or None when history unavailable.
HistoryLookupFn = Callable[[str], list[tuple[str, float]] | None]

UNKNOWN_SECTOR = "Unknown"
MIN_OVERLAP_DAYS = 60
TOP_CORRELATIONS = 10
CORRELATION_WINDOW = "~1y daily returns"


def _sector_from_result(result: Phase0Result | None) -> str | None:
    if result is None or result.fundamentals is None:
        return None
    profile = result.fundamentals.profile
    if profile is None or not profile.sector:
        return None
    sector = profile.sector.strip()
    return sector or None


def _risk_score(
    ticker: str,
    *,
    summary_score: float | None,
    result: Phase0Result | None,
) -> float | None:
    if summary_score is not None:
        return summary_score
    if result is not None and result.scorecard is not None:
        return result.scorecard.risk_score
    return None


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 2:
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = 0.0
    den_x = 0.0
    den_y = 0.0
    for x, y in zip(xs, ys, strict=True):
        dx = x - mean_x
        dy = y - mean_y
        num += dx * dy
        den_x += dx * dx
        den_y += dy * dy
    if den_x <= 0.0 or den_y <= 0.0:
        return None
    corr = num / math.sqrt(den_x * den_y)
    if not math.isfinite(corr):
        return None
    # Clamp tiny floating error outside [-1, 1]
    return max(-1.0, min(1.0, corr))


def _pair_correlation(
    returns_a: dict[str, float],
    returns_b: dict[str, float],
) -> tuple[float, int] | None:
    common = sorted(set(returns_a) & set(returns_b))
    if len(common) < MIN_OVERLAP_DAYS:
        return None
    xs = [returns_a[d] for d in common]
    ys = [returns_b[d] for d in common]
    corr = _pearson(xs, ys)
    if corr is None:
        return None
    return corr, len(common)


def compute_top_correlations(
    held: list[str],
    history_by_ticker: dict[str, list[tuple[str, float]] | None],
    *,
    top_n: int = TOP_CORRELATIONS,
) -> tuple[list[PairCorrelation], list[str]]:
    """Return top pairs by |correlation| and correlation-related gaps."""
    gaps: list[str] = []
    if len(held) < 2:
        return [], gaps

    returns_map: dict[str, dict[str, float]] = {}
    for ticker in held:
        closes = history_by_ticker.get(ticker)
        if closes is None:
            gaps.append(f"{ticker}: price history missing (Yahoo source cache)")
            continue
        returns_map[ticker] = daily_returns(closes)

    pairs: list[PairCorrelation] = []
    for i, a in enumerate(held):
        if a not in returns_map:
            continue
        for b in held[i + 1 :]:
            if b not in returns_map:
                continue
            result = _pair_correlation(returns_map[a], returns_map[b])
            if result is None:
                continue
            corr, overlap = result
            ta, tb = sorted((a, b))
            pairs.append(
                PairCorrelation(
                    ticker_a=ta,
                    ticker_b=tb,
                    correlation=corr,
                    overlap_days=overlap,
                    window=CORRELATION_WINDOW,
                )
            )

    pairs.sort(
        key=lambda p: (-abs(p.correlation), p.ticker_a, p.ticker_b),
    )
    top = pairs[:top_n]

    if not top:
        gaps.append(
            "correlation: insufficient overlapping history for any Held pair "
            f"(need ≥{MIN_OVERLAP_DAYS} shared return days)"
        )

    return top, gaps


def build_portfolio_risk(
    *,
    app_settings: Settings | None = None,
    cache_lookup_fn: CacheLookupFn | None = None,
    history_lookup_fn: HistoryLookupFn | None = None,
) -> PortfolioRiskSnapshot:
    """Build Held-only concentration + correlation snapshot (equal-weight)."""
    s = app_settings if app_settings is not None else default_settings
    lookup = cache_lookup_fn or cache_lookup
    membership = store.get_membership(s)
    held = list(membership.held)
    summaries = {row.ticker.upper(): row for row in store.get_summaries(s)}

    if not held:
        return PortfolioRiskSnapshot(
            status=Phase0Status.OK,
            held_count=0,
            equal_weight=True,
            disclaimer=PHASE0_DISCLAIMER,
        )

    n = len(held)
    weight = 1.0 / n
    positions: list[HeldPositionRisk] = []
    sector_tickers: dict[str, list[str]] = defaultdict(list)
    gaps: list[str] = []
    risk_values: list[float] = []

    for ticker in held:
        summary = summaries.get(ticker)
        try:
            result = lookup(
                ticker,
                cache_dir=s.phase0_cache_dir,
                ttl_seconds=s.phase0_cache_ttl_seconds,
            )
        except TypeError:
            # Injected test doubles may ignore kwargs.
            result = lookup(ticker)

        sector = _sector_from_result(result)
        risk_score = _risk_score(
            ticker,
            summary_score=summary.risk_score if summary else None,
            result=result,
        )
        row_status = summary.status if summary else None
        if row_status is None and result is not None:
            row_status = result.status

        if sector is None:
            gaps.append(f"{ticker}: sector unknown (refresh research or cache miss)")
            bucket = UNKNOWN_SECTOR
        else:
            bucket = sector

        if risk_score is None:
            gaps.append(f"{ticker}: risk score missing")
        else:
            risk_values.append(risk_score)

        if row_status is None:
            gaps.append(f"{ticker}: no research summary yet")
        elif row_status == Phase0Status.ERROR:
            gaps.append(f"{ticker}: research status error")

        positions.append(
            HeldPositionRisk(
                ticker=ticker,
                weight=weight,
                sector=sector,
                risk_score=risk_score,
                status=row_status,
            )
        )
        sector_tickers[bucket].append(ticker)

    buckets = [
        SectorBucket(
            sector=sector,
            weight=len(tickers) / n,
            count=len(tickers),
            tickers=list(tickers),
        )
        for sector, tickers in sorted(
            sector_tickers.items(),
            key=lambda item: (-len(item[1]), item[0].lower()),
        )
    ]

    # Correlation from Yahoo source-cache history (no live refetch).
    hist_lookup = history_lookup_fn
    if hist_lookup is None:

        def hist_lookup(ticker: str) -> list[tuple[str, float]] | None:
            return lookup_history_closes(ticker, app_settings=s)

    history_by_ticker: dict[str, list[tuple[str, float]] | None] = {
        t: hist_lookup(t) for t in held
    }
    top_correlations, corr_gaps = compute_top_correlations(held, history_by_ticker)
    gaps.extend(corr_gaps)

    avg_risk = sum(risk_values) / len(risk_values) if risk_values else None
    status = Phase0Status.PARTIAL if gaps else Phase0Status.OK

    logger.info(
        "portfolio_risk held_count=%s status=%s gaps=%s corr_pairs=%s",
        n,
        status.value,
        len(gaps),
        len(top_correlations),
    )

    return PortfolioRiskSnapshot(
        status=status,
        held_count=n,
        equal_weight=True,
        positions=positions,
        sector_buckets=buckets,
        top_correlations=top_correlations,
        correlation_pairs_known=len(top_correlations),
        top_name_weight=weight,
        avg_risk_score=avg_risk,
        risk_scores_known=len(risk_values),
        gaps=gaps,
        disclaimer=PHASE0_DISCLAIMER,
    )

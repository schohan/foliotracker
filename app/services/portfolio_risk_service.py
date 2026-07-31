"""Portfolio Risk v1 — equal-weight concentration for Held names.

Pure calculation over membership + cached Phase0 / summaries. Never invents
sector or scores; gaps surface as ``partial``.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Callable

from app.configs.settings import Settings, settings as default_settings
from app.schemas.phase0 import PHASE0_DISCLAIMER, Phase0Result, Phase0Status
from app.schemas.portfolio import (
    HeldPositionRisk,
    PortfolioRiskSnapshot,
    SectorBucket,
)
from app.services import watchlist_store as store
from app.services.phase0_cache import cache_lookup

logger = logging.getLogger(__name__)

CacheLookupFn = Callable[..., Phase0Result | None]

UNKNOWN_SECTOR = "Unknown"


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


def build_portfolio_risk(
    *,
    app_settings: Settings | None = None,
    cache_lookup_fn: CacheLookupFn | None = None,
) -> PortfolioRiskSnapshot:
    """Build Held-only concentration snapshot (equal-weight)."""
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

    avg_risk = sum(risk_values) / len(risk_values) if risk_values else None
    status = Phase0Status.PARTIAL if gaps else Phase0Status.OK

    logger.info(
        "portfolio_risk held_count=%s status=%s gaps=%s",
        n,
        status.value,
        len(gaps),
    )

    return PortfolioRiskSnapshot(
        status=status,
        held_count=n,
        equal_weight=True,
        positions=positions,
        sector_buckets=buckets,
        top_name_weight=weight,
        avg_risk_score=avg_risk,
        risk_scores_known=len(risk_values),
        gaps=gaps,
        disclaimer=PHASE0_DISCLAIMER,
    )

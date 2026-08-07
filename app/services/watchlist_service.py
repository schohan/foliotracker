"""Watchlist orchestration — membership + Phase0 refresh → summaries."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

from app.configs.settings import Settings, settings as default_settings
from app.schemas.phase0 import PHASE0_DISCLAIMER, Phase0Result
from app.schemas.ticker import InvalidTickerError, normalize_ticker
from app.schemas.watchlist import (
    BatchRefreshResponse,
    ListKind,
    WatchlistState,
    WatchlistTickerSummary,
    summary_from_phase0,
)
from app.services import watchlist_store as store
from app.services.phase0_pipeline import run_phase0_research

logger = logging.getLogger(__name__)

ResearchFn = Callable[..., Phase0Result]


def get_watchlist_state(app_settings: Settings | None = None) -> WatchlistState:
    s = app_settings if app_settings is not None else default_settings
    return WatchlistState(
        membership=store.get_membership(s),
        summaries=store.get_summaries(s),
        collections=store.list_collections(s),
        disclaimer=PHASE0_DISCLAIMER,
    )


def refresh_ticker(
    ticker: str,
    *,
    app_settings: Settings | None = None,
    research_fn: ResearchFn | None = None,
    skip_cache: bool = False,
) -> WatchlistTickerSummary:
    """Run Phase0 for one membership ticker and persist summary."""
    s = app_settings if app_settings is not None else default_settings
    normalized = normalize_ticker(ticker)
    kind = store.list_kind_for(normalized, app_settings=s)
    if kind is None:
        raise LookupError(f"{normalized} is not on the watchlist")
    fn = research_fn or run_phase0_research
    result = fn(normalized, skip_cache=skip_cache)
    summary = summary_from_phase0(
        result,
        list_kind=kind,
        updated_at=store.now_utc(),
    )
    store.upsert_summary(summary, s)
    return summary


def refresh_batch(
    *,
    tickers: list[str] | None = None,
    max_tickers: int = 8,
    app_settings: Settings | None = None,
    research_fn: ResearchFn | None = None,
    skip_cache: bool = False,
    max_workers: int = 1,
) -> BatchRefreshResponse:
    """Refresh up to ``max_tickers`` membership symbols.

    Defaults to sequential workers so per-source min-interval pacing
    (e.g. Alpha Vantage window/calls) is respected during bulk refresh.
    """
    s = app_settings if app_settings is not None else default_settings
    membership = store.get_membership(s)
    all_members = list(membership.held) + list(membership.watched)
    if tickers:
        wanted: list[str] = []
        for raw in tickers:
            try:
                t = normalize_ticker(raw)
            except InvalidTickerError:
                continue
            if t in all_members and t not in wanted:
                wanted.append(t)
        target = wanted
    else:
        target = all_members

    skipped = target[max_tickers:]
    target = target[:max_tickers]
    refreshed: list[str] = []
    summaries: list[WatchlistTickerSummary] = []

    def _one(t: str) -> WatchlistTickerSummary:
        return refresh_ticker(
            t,
            app_settings=s,
            research_fn=research_fn,
            skip_cache=skip_cache,
        )

    skipped_norm = list(skipped)

    if not target:
        return BatchRefreshResponse(
            summaries=store.get_summaries(s),
            refreshed=[],
            skipped=skipped_norm,
        )

    with ThreadPoolExecutor(max_workers=max(1, min(max_workers, len(target)))) as pool:
        futures = {pool.submit(_one, t): t for t in target}
        for fut in as_completed(futures):
            t = futures[fut]
            try:
                summary = fut.result()
                summaries.append(summary)
                refreshed.append(t)
            except Exception as exc:  # noqa: BLE001
                logger.warning("watchlist_refresh_failed ticker=%s err=%s", t, exc)
                kind = store.list_kind_for(t, app_settings=s) or ListKind.WATCHED
                summaries.append(
                    WatchlistTickerSummary(
                        ticker=t,
                        list_kind=kind,
                        error_message=str(exc),
                    )
                )

    # Stable order: membership order
    by_ticker = {x.ticker: x for x in summaries}
    ordered = [by_ticker[t] for t in target if t in by_ticker]
    return BatchRefreshResponse(
        summaries=ordered,
        refreshed=refreshed,
        skipped=skipped_norm,
        disclaimer=PHASE0_DISCLAIMER,
    )

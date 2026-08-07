"""Thesis page generator (T1 frameworks + T2 valuation / net assets / MoS).

Cache-first fan-out over Held ∪ Watched: merged fundamentals (Yahoo +
SEC XBRL + optional Alpha Vantage via ``cached_fetch`` + ``merge_fundamentals``)
→ deterministic framework scorecards + valuation set + asset breakdown.
Does **not** call ``run_phase0_research``. Brief is untouched (Engine 1
preserved).
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Callable

from app.configs.settings import Settings, settings as default_settings
from app.schemas.financials import FinancialMetrics
from app.schemas.phase0 import PHASE0_DISCLAIMER
from app.schemas.thesis import (
    FrameworkId,
    ThesisDashboard,
    ThesisGenerationStatus,
    ThesisTicker,
)
from app.schemas.watchlist import ListKind
from app.services import thesis_store, watchlist_store as store
from app.services.merge_fundamentals import ProviderSnapshot, merge_fundamentals
from app.services.source_fetch import cached_fetch
from app.services.source_registry import (
    SOURCE_ALPHA_VANTAGE,
    SOURCE_SEC_XBRL,
    SOURCE_YAHOO,
)
from app.services.thesis_frameworks import scorecards_for
from app.services.thesis_net_assets import asset_breakdown_for
from app.services.thesis_valuations import margin_of_safety_for, valuation_set_for
from app.tools.filings.sec_xbrl import fetch_sec_xbrl_fundamentals
from app.tools.finance.alpha_vantage import fetch_alpha_vantage_fundamentals
from app.tools.finance.yahoo_finance import fetch_financial_metrics

logger = logging.getLogger(__name__)

EMPTY_UNIVERSE_MSG = "Add tickers on Watchlist to build the Thesis table."

TickerWorkerFn = Callable[[str, ListKind], "ThesisTicker"]


def _universe(held: list[str], watched: list[str]) -> list[tuple[str, ListKind]]:
    """Held ∪ Watched; Held wins duplicates; held listed first."""
    seen: set[str] = set()
    out: list[tuple[str, ListKind]] = []
    for t in held:
        if t not in seen:
            out.append((t, ListKind.HELD))
            seen.add(t)
    for t in watched:
        if t not in seen:
            out.append((t, ListKind.WATCHED))
            seen.add(t)
    return out


def _merged_fundamentals(
    ticker: str,
    *,
    app_settings: Settings,
    force_refresh: bool,
) -> tuple[FinancialMetrics, list[str], list[str]]:
    """Cache-first Yahoo + SEC XBRL (+ AV when keyed) → merged snapshot.

    Returns (merged snapshot, sources_used, gaps). Per-source failure is a
    gap, never fatal — an empty merge yields all-unknown scorecards.
    """
    gaps: list[str] = []
    providers: list[ProviderSnapshot] = []

    def _try(source_id: str, fetch: Callable[[], FinancialMetrics]) -> None:
        try:
            res = cached_fetch(
                source_id,
                ticker,
                fetch,
                FinancialMetrics,
                app_settings=app_settings,
                force_refresh=force_refresh,
            )
            providers.append(ProviderSnapshot(source_id=source_id, snapshot=res.data))
        except Exception as exc:  # noqa: BLE001 — per-source degrade
            gaps.append(f"{ticker}: {source_id} unavailable ({exc.__class__.__name__})")
            logger.info(
                "thesis_source_fail ticker=%s source=%s err=%s",
                ticker,
                source_id,
                exc,
            )

    _try(SOURCE_YAHOO, lambda: fetch_financial_metrics(ticker))
    _try(SOURCE_SEC_XBRL, lambda: fetch_sec_xbrl_fundamentals(ticker))
    if app_settings.alpha_vantage_api_key:
        _try(SOURCE_ALPHA_VANTAGE, lambda: fetch_alpha_vantage_fundamentals(ticker))

    merge_result = merge_fundamentals(list(providers), ticker=ticker)
    return merge_result.snapshot, merge_result.sources_used, gaps


def build_thesis_ticker(
    ticker: str,
    list_kind: ListKind,
    *,
    app_settings: Settings,
    force_refresh: bool = False,
) -> ThesisTicker:
    """One row: merged fundamentals → frameworks + valuation + assets."""
    merged, sources_used, gaps = _merged_fundamentals(
        ticker,
        app_settings=app_settings,
        force_refresh=force_refresh,
    )
    profile = merged.profile
    return ThesisTicker(
        ticker=ticker,
        list_kind=list_kind.value,  # type: ignore[arg-type]
        name=profile.name if profile is not None else None,
        sector=profile.sector if profile is not None else None,
        frameworks=scorecards_for(merged),
        valuation=valuation_set_for(merged),
        margin_of_safety=margin_of_safety_for(merged),
        assets=asset_breakdown_for(merged),
        sources_used=sources_used,
        gaps=gaps,
    )


def generate_thesis_dashboard(
    *,
    app_settings: Settings | None = None,
    force_refresh: bool = False,
    worker_fn: TickerWorkerFn | None = None,
    now: datetime | None = None,
) -> ThesisDashboard:
    """Sync Generate over membership snapshot; wall budget → partial."""
    s = app_settings if app_settings is not None else default_settings
    clock = now or datetime.now(timezone.utc)
    if clock.tzinfo is None:
        clock = clock.replace(tzinfo=timezone.utc)

    membership = store.get_membership(s)
    universe = _universe(list(membership.held), list(membership.watched))
    if not universe:
        dashboard = ThesisDashboard(
            generated_at=clock,
            generation_status=ThesisGenerationStatus.COMPLETE,
            universe_count=0,
            tickers_considered=0,
            tickers=[],
            frameworks=list(FrameworkId),
            empty_message=EMPTY_UNIVERSE_MSG,
            disclaimer=PHASE0_DISCLAIMER,
        )
        thesis_store.save_dashboard(dashboard, app_settings=s)
        return dashboard

    wall = float(s.thesis_generate_budget_seconds)
    workers = max(1, min(int(s.thesis_max_workers), 8))

    def default_worker(ticker: str, list_kind: ListKind) -> ThesisTicker:
        return build_thesis_ticker(
            ticker,
            list_kind,
            app_settings=s,
            force_refresh=force_refresh,
        )

    worker = worker_fn or default_worker

    start = time.monotonic()
    rows: list[ThesisTicker] = []
    gaps: list[str] = []
    timed_out = False
    considered = 0

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(worker, ticker, kind): (ticker, kind)
            for ticker, kind in universe
        }
        for fut in as_completed(futures):
            if time.monotonic() - start >= wall:
                timed_out = True
                break
            ticker, _kind = futures[fut]
            considered += 1
            try:
                rows.append(fut.result())
            except Exception as exc:  # noqa: BLE001
                gaps.append(f"{ticker}: worker failed ({exc.__class__.__name__})")
                logger.warning("thesis_worker_fail ticker=%s err=%s", ticker, exc)

        if timed_out:
            for fut in futures:
                fut.cancel()
            remaining = len(universe) - considered
            if remaining > 0:
                gaps.append(
                    f"generate budget {wall:.0f}s hit; {remaining} tickers not finished"
                )

    for row in rows:
        gaps.extend(row.gaps)

    # Held first, then alphabetical (stable, scan-friendly table).
    rows.sort(key=lambda r: (r.list_kind != "held", r.ticker))

    status = (
        ThesisGenerationStatus.PARTIAL
        if timed_out or gaps
        else ThesisGenerationStatus.COMPLETE
    )

    dashboard = ThesisDashboard(
        generated_at=clock,
        generation_status=status,
        universe_count=len(universe),
        tickers_considered=considered,
        tickers=rows,
        frameworks=list(FrameworkId),
        gaps=gaps,
        empty_message=None,
        disclaimer=PHASE0_DISCLAIMER,
    )
    thesis_store.save_dashboard(dashboard, app_settings=s)
    logger.info(
        "thesis_generated universe=%s considered=%s rows=%s status=%s",
        len(universe),
        considered,
        len(rows),
        status.value,
    )
    return dashboard


def get_latest_dashboard(
    *, app_settings: Settings | None = None
) -> ThesisDashboard | None:
    return thesis_store.get_latest_dashboard(app_settings)

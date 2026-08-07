"""Thesis page generator (T1–T4: frameworks + valuation + monitoring + advisor).

Cache-first fan-out over Held ∪ Watched: merged fundamentals → framework
scorecards + valuation + asset breakdown + thesis monitoring (quarterly
verdicts) + AI Portfolio Advisor. Does **not** call ``run_phase0_research``.
Brief is untouched.
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
    ThesisExplainAnswer,
    ThesisGenerationStatus,
    ThesisMonitoring,
    ThesisSnapshot,
    ThesisTicker,
)
from app.schemas.ticker import InvalidTickerError, normalize_ticker
from app.schemas.watchlist import ListKind
from app.services import thesis_store, watchlist_store as store
from app.services.merge_fundamentals import ProviderSnapshot, merge_fundamentals
from app.services.phase0_cache import cache_lookup_stale
from app.services.source_fetch import cached_fetch
from app.services.source_registry import (
    SOURCE_ALPHA_VANTAGE,
    SOURCE_SEC_XBRL,
    SOURCE_YAHOO,
)
from app.services.thesis_advisor import build_advisor, explain_for_row
from app.services.thesis_frameworks import scorecards_for
from app.services.thesis_insight import narrate_change
from app.services.thesis_monitor import (
    assess_change,
    should_append_snapshot,
    signals_from,
    synthesize_original_thesis,
)
from app.services.thesis_net_assets import asset_breakdown_for
from app.services.thesis_valuations import margin_of_safety_for, valuation_set_for
from app.tools.filings.sec_xbrl import fetch_sec_xbrl_fundamentals
from app.tools.finance.alpha_vantage import fetch_alpha_vantage_fundamentals
from app.tools.finance.yahoo_finance import fetch_financial_metrics

logger = logging.getLogger(__name__)

EMPTY_UNIVERSE_MSG = "Add tickers on Watchlist to build the Thesis table."

TickerWorkerFn = Callable[[str, ListKind], "ThesisTicker"]


class ThesisExplainError(ValueError):
    """Raised when explain cannot resolve a ticker row."""


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
    """Cache-first Yahoo + SEC XBRL (+ AV when keyed) → merged snapshot."""
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


def _seed_original_thesis(
    ticker: str,
    *,
    prior: ThesisSnapshot | None,
    signals,
    app_settings: Settings,
) -> str:
    if prior is not None and prior.original_thesis.strip():
        return prior.original_thesis
    cached = cache_lookup_stale(ticker, cache_dir=app_settings.phase0_cache_dir)
    if cached is not None and cached.thesis is not None and cached.thesis.thesis.strip():
        return cached.thesis.thesis.strip()
    return synthesize_original_thesis(
        graham_score=signals.graham_score,
        fs_score=signals.fs_score,
        mos=signals.mos,
    )


def build_thesis_ticker(
    ticker: str,
    list_kind: ListKind,
    *,
    app_settings: Settings,
    force_refresh: bool = False,
    now: datetime | None = None,
) -> ThesisTicker:
    """One row: merged fundamentals → frameworks + valuation + monitoring + advisor."""
    clock = now or datetime.now(timezone.utc)
    if clock.tzinfo is None:
        clock = clock.replace(tzinfo=timezone.utc)

    merged, sources_used, gaps = _merged_fundamentals(
        ticker,
        app_settings=app_settings,
        force_refresh=force_refresh,
    )
    frameworks = scorecards_for(merged)
    mos_view = margin_of_safety_for(merged)
    valuation = valuation_set_for(merged)
    assets = asset_breakdown_for(merged)

    current_signals = signals_from(
        frameworks=frameworks,
        mos_view=mos_view,
        metrics=merged,
    )
    prior = thesis_store.get_latest_snapshot(ticker, app_settings=app_settings)
    original = _seed_original_thesis(
        ticker,
        prior=prior,
        signals=current_signals,
        app_settings=app_settings,
    )
    prior_signals = prior.signals if prior is not None else None
    change = assess_change(prior_signals, current_signals, as_of=clock)
    change = narrate_change(
        change,
        ticker=ticker,
        original_thesis=original,
        app_settings=app_settings,
    )

    framework_scores = {c.framework.value: c.score for c in frameworks}
    if should_append_snapshot(
        prior.as_of if prior is not None else None,
        now=clock,
        quarter_days=int(getattr(app_settings, "thesis_quarter_days", 90)),
        force_refresh=force_refresh,
    ):
        snap = ThesisSnapshot(
            ticker=ticker.upper(),
            as_of=clock,
            original_thesis=original,
            signals=current_signals,
            change=change,
            framework_scores=framework_scores,
        )
        thesis_store.append_snapshot(snap, app_settings=app_settings)

    snaps = thesis_store.get_snapshots(ticker, app_settings=app_settings)
    timeline = [s.change for s in snaps]
    # Prefer freshly computed current even if ring was not appended.
    monitoring = ThesisMonitoring(
        original_thesis=original,
        current=change,
        timeline=timeline if timeline else [change],
    )
    advisor = build_advisor(
        ticker=ticker,
        frameworks=frameworks,
        mos_view=mos_view,
        assets=assets,
        monitoring=monitoring,
        app_settings=app_settings,
    )

    profile = merged.profile
    return ThesisTicker(
        ticker=ticker,
        list_kind=list_kind.value,  # type: ignore[arg-type]
        name=profile.name if profile is not None else None,
        sector=profile.sector if profile is not None else None,
        frameworks=frameworks,
        valuation=valuation,
        margin_of_safety=mos_view,
        assets=assets,
        monitoring=monitoring,
        advisor=advisor,
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
            now=clock,
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


def explain_thesis(
    *,
    ticker: str,
    question_id: str = "",
    question: str = "",
    app_settings: Settings | None = None,
) -> ThesisExplainAnswer:
    """On-demand research-button answer from the latest dashboard row."""
    s = app_settings if app_settings is not None else default_settings
    try:
        sym = normalize_ticker(ticker)
    except InvalidTickerError as exc:
        raise ThesisExplainError(str(exc)) from exc

    dash = thesis_store.get_latest_dashboard(app_settings=s)
    if dash is None:
        raise ThesisExplainError("No thesis dashboard yet — Generate first.")
    row = next((t for t in dash.tickers if t.ticker == sym), None)
    if row is None:
        raise ThesisExplainError(f"{sym} not in the latest thesis table.")
    return explain_for_row(
        row,
        question_id=question_id,
        question=question,
        app_settings=s,
    )

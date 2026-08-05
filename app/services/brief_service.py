"""Daily Decision Brief generator (triage-first).

Cache-first fan-out over Held ∪ Watched via ``cached_fetch`` + ``evidence_from_*``.
Does **not** call ``run_phase0_research``. Phase0 cache is optional for metrics strip.
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Callable

from app.configs.settings import Settings, settings as default_settings
from app.schemas.brief import (
    BriefBullet,
    BriefEventCategory,
    BriefGenerationStatus,
    BriefInsightMode,
    BriefMarketRisk,
    BriefPriority,
    BriefSentiment,
    BriefSummary,
    BriefTicker,
    BriefTickerStatus,
    DailyBrief,
    QuietTicker,
)
from app.schemas.evidence import Evidence
from app.schemas.filings import SecFilingsBatch
from app.schemas.financials import FinancialMetrics
from app.schemas.news import NewsBatch
from app.schemas.phase0 import PHASE0_DISCLAIMER, Phase0Result
from app.schemas.watchlist import ListKind
from app.services import brief_store, watchlist_store as store
from app.services.brief_classify import ClassifiedEvent, classify_evidence
from app.services.brief_impact import (
    category_headline,
    event_key,
    impact_from_category,
    portfolio_impact_line,
    priority_from_impact,
    sentiment_from_text,
    sources_for_bullet,
    theme_label,
)
from app.services.brief_insight import (
    build_insight,
    confidence_for_event,
    parse_insight_mode,
    why_it_matters_bullets,
)
from app.services.evidence import evidence_from_filings, evidence_from_news
from app.services.phase0_cache import cache_lookup
from app.services.source_fetch import cached_fetch
from app.services.source_registry import (
    SOURCE_GOOGLE_NEWS,
    SOURCE_SEC_EDGAR,
    SOURCE_YAHOO,
)
from app.services.yahoo_history import (
    last_session_daily_return,
    move_score,
    parse_history_closes,
    passes_move_gate,
)
from app.tools.filings.sec_edgar import fetch_sec_filings
from app.tools.finance.yahoo_finance import fetch_financial_metrics
from app.tools.news.google_news import fetch_google_news

logger = logging.getLogger(__name__)

EMPTY_UNIVERSE_MSG = "Add tickers on Watchlist to generate a Brief."
EMPTY_MATERIAL_MSG = "Nothing material in the last 24h."

TickerWorkerFn = Callable[[str, ListKind], "TickerWorkResult"]


class TickerWorkResult:
    __slots__ = (
        "ticker",
        "list_kind",
        "daily_return",
        "events",
        "bundle_ids",
        "metrics",
        "phase0",
        "gaps",
        "sources_partial",
    )

    def __init__(
        self,
        ticker: str,
        list_kind: ListKind,
        *,
        daily_return: float | None,
        events: list[ClassifiedEvent],
        bundle_ids: set[str],
        metrics: FinancialMetrics | None,
        phase0: Phase0Result | None,
        gaps: list[str],
        sources_partial: bool,
    ) -> None:
        self.ticker = ticker
        self.list_kind = list_kind
        self.daily_return = daily_return
        self.events = events
        self.bundle_ids = bundle_ids
        self.metrics = metrics
        self.phase0 = phase0
        self.gaps = gaps
        self.sources_partial = sources_partial


def _universe(membership_held: list[str], membership_watched: list[str]) -> list[tuple[str, ListKind]]:
    """Held ∪ Watched; Held wins duplicates; held listed first."""
    seen: set[str] = set()
    out: list[tuple[str, ListKind]] = []
    for t in membership_held:
        if t not in seen:
            out.append((t, ListKind.HELD))
            seen.add(t)
    for t in membership_watched:
        if t not in seen:
            out.append((t, ListKind.WATCHED))
            seen.add(t)
    return out


def _fetch_ticker_sources(
    ticker: str,
    list_kind: ListKind,
    *,
    app_settings: Settings,
    force_refresh: bool,
    now: datetime,
    window_hours: int,
) -> TickerWorkResult:
    gaps: list[str] = []
    sources_partial = False
    metrics: FinancialMetrics | None = None
    news_batch: NewsBatch | None = None
    filings_batch: SecFilingsBatch | None = None

    try:
        yahoo_res = cached_fetch(
            SOURCE_YAHOO,
            ticker,
            lambda: fetch_financial_metrics(ticker),
            FinancialMetrics,
            app_settings=app_settings,
            force_refresh=force_refresh,
        )
        metrics = yahoo_res.data
    except Exception as exc:  # noqa: BLE001 — per-ticker degrade
        sources_partial = True
        gaps.append(f"{ticker}: yahoo unavailable ({exc.__class__.__name__})")
        logger.info("brief_yahoo_fail ticker=%s err=%s", ticker, exc)

    try:
        news_res = cached_fetch(
            SOURCE_GOOGLE_NEWS,
            ticker,
            lambda: fetch_google_news(ticker),
            NewsBatch,
            app_settings=app_settings,
            force_refresh=force_refresh,
        )
        news_batch = news_res.data
    except Exception as exc:  # noqa: BLE001
        sources_partial = True
        gaps.append(f"{ticker}: news unavailable ({exc.__class__.__name__})")
        logger.info("brief_news_fail ticker=%s err=%s", ticker, exc)

    try:
        sec_res = cached_fetch(
            SOURCE_SEC_EDGAR,
            ticker,
            lambda: fetch_sec_filings(ticker),
            SecFilingsBatch,
            app_settings=app_settings,
            force_refresh=force_refresh,
        )
        filings_batch = sec_res.data
    except Exception as exc:  # noqa: BLE001
        sources_partial = True
        gaps.append(f"{ticker}: sec unavailable ({exc.__class__.__name__})")
        logger.info("brief_sec_fail ticker=%s err=%s", ticker, exc)

    evidence_items: list[Evidence] = []
    if news_batch is not None:
        evidence_items.extend(evidence_from_news(news_batch))
    if filings_batch is not None:
        evidence_items.extend(evidence_from_filings(filings_batch))
    bundle_ids = {e.id for e in evidence_items}

    events = classify_evidence(
        evidence_items,
        now=now,
        window_hours=window_hours,
    )

    closes = None
    if metrics is not None:
        closes = parse_history_closes(metrics.model_dump(mode="json"))
    daily_ret = last_session_daily_return(closes)

    phase0: Phase0Result | None = None
    try:
        phase0 = cache_lookup(
            ticker,
            cache_dir=app_settings.phase0_cache_dir,
            ttl_seconds=app_settings.phase0_cache_ttl_seconds,
        )
    except Exception:  # noqa: BLE001
        phase0 = None

    return TickerWorkResult(
        ticker=ticker,
        list_kind=list_kind,
        daily_return=daily_ret,
        events=events,
        bundle_ids=bundle_ids,
        metrics=metrics,
        phase0=phase0,
        gaps=gaps,
        sources_partial=sources_partial,
    )


def _enrich_bullet(
    *,
    ticker: str,
    list_kind: str,
    daily_return: float | None,
    move_sc: int | None,
    category: BriefEventCategory,
    severity: int,
    text: str,
    evidence_ids: list[str],
    source_url: str | None,
    held_count: int,
    insight_mode: BriefInsightMode,
    app_settings: Settings,
) -> BriefBullet:
    impact = impact_from_category(
        category,
        severity=severity,
        move_score=move_sc,
        daily_return=daily_return,
    )
    priority = priority_from_impact(impact) or BriefPriority.MEDIUM
    sentiment = sentiment_from_text(
        text, daily_return=daily_return, category=category
    )
    conf = confidence_for_event(
        category=category,
        has_source_url=bool(source_url),
        severity=severity,
    )
    insight = build_insight(
        ticker=ticker,
        category=category,
        text=text,
        list_kind=list_kind,
        daily_return=daily_return,
        sentiment=sentiment,
        impact=impact,
        confidence=conf,
        mode=insight_mode,
        app_settings=app_settings,
    )
    headline = category_headline(category)
    return BriefBullet(
        text=text,
        category=category,
        severity=severity,
        evidence_ids=evidence_ids,
        source_url=source_url,
        event_key=event_key(
            ticker, category, text, evidence_ids[0] if evidence_ids else None
        ),
        impact_score=impact,
        priority=priority,
        sentiment=sentiment,
        headline=headline,
        one_line_summary=text[:180],
        why_it_matters=why_it_matters_bullets(
            category=category,
            list_kind=list_kind,
            sentiment=sentiment,
            daily_return=daily_return,
        ),
        portfolio_impact=portfolio_impact_line(
            list_kind=list_kind, held_count=held_count
        ),
        suggested_action=insight.suggested_action,
        confidence=conf,
        sources=sources_for_bullet(
            source_url=source_url,
            category=category,
            evidence_ids=evidence_ids,
        ),
        insight=insight,
    )


def _bullets_from_events(
    events: list[ClassifiedEvent],
    *,
    ticker: str,
    list_kind: str,
    daily_return: float | None,
    move_sc: int | None,
    max_bullets: int,
    held_count: int,
    insight_mode: BriefInsightMode,
    app_settings: Settings,
) -> list[BriefBullet]:
    bullets: list[BriefBullet] = []
    for ev in events:
        if len(bullets) >= max_bullets:
            break
        eid = ev.evidence.id
        if not eid and not ev.source_url:
            continue
        bullets.append(
            _enrich_bullet(
                ticker=ticker,
                list_kind=list_kind,
                daily_return=daily_return,
                move_sc=move_sc,
                category=ev.category,
                severity=ev.severity,
                text=ev.title,
                evidence_ids=[eid] if eid else [],
                source_url=ev.source_url,
                held_count=held_count,
                insight_mode=insight_mode,
                app_settings=app_settings,
            )
        )
    return bullets


def _price_move_bullet(
    *,
    ticker: str,
    list_kind: str,
    daily_return: float,
    move_sc: int,
    held_count: int,
    insight_mode: BriefInsightMode,
    app_settings: Settings,
) -> BriefBullet:
    pct = daily_return * 100
    sign = "+" if pct > 0 else ""
    text = f"Session move {sign}{pct:.1f}% without a classified headline"
    return _enrich_bullet(
        ticker=ticker,
        list_kind=list_kind,
        daily_return=daily_return,
        move_sc=move_sc,
        category=BriefEventCategory.PRICE_MOVE,
        severity=max(2, min(5, move_sc)),
        text=text,
        evidence_ids=[],
        source_url=None,
        held_count=held_count,
        insight_mode=insight_mode,
        app_settings=app_settings,
    )


def _metrics_strip(
    work: TickerWorkResult,
) -> dict[str, float | None]:
    trailing_pe = None
    return_1y = None
    growth = value = risk = None
    if work.metrics is not None:
        trailing_pe = work.metrics.trailing_pe or work.metrics.pe_ratio
        if work.metrics.returns is not None:
            return_1y = work.metrics.returns.return_1y
    if work.phase0 is not None:
        sc = work.phase0.scorecard
        if sc is not None:
            growth = sc.growth_score
            value = sc.value_score
            risk = sc.risk_score
        fund = work.phase0.fundamentals
        if fund is not None:
            if trailing_pe is None:
                trailing_pe = fund.trailing_pe or fund.pe_ratio
            if return_1y is None and fund.returns is not None:
                return_1y = fund.returns.return_1y
    return {
        "trailing_pe": trailing_pe,
        "return_1y": return_1y,
        "growth_score": growth,
        "value_score": value,
        "risk_score": risk,
    }


def build_ticker_row(
    work: TickerWorkResult,
    *,
    max_bullets: int,
    held_count: int = 0,
    insight_mode: BriefInsightMode | None = None,
    app_settings: Settings | None = None,
) -> BriefTicker | None:
    """Apply material gate; return row or None for quiet names."""
    s = app_settings if app_settings is not None else default_settings
    mode = insight_mode or parse_insight_mode(s.brief_insight_mode)
    mscore = move_score(work.daily_return)
    list_kind = work.list_kind.value
    bullets = _bullets_from_events(
        work.events,
        ticker=work.ticker,
        list_kind=list_kind,
        daily_return=work.daily_return,
        move_sc=mscore,
        max_bullets=max_bullets,
        held_count=held_count,
        insight_mode=mode,
        app_settings=s,
    )
    move_ok = passes_move_gate(work.daily_return)
    event_ok = len(bullets) > 0

    if not move_ok and not event_ok:
        if work.daily_return is None and work.metrics is None and work.sources_partial:
            strip = _metrics_strip(work)
            return BriefTicker(
                ticker=work.ticker,
                list_kind=list_kind,  # type: ignore[arg-type]
                status=BriefTickerStatus.UNAVAILABLE,
                daily_return=None,
                move_score=None,
                event_severity=None,
                rank_score=0.0,
                impact_score=0,
                priority=None,
                bullets=[],
                **strip,
            )
        return None

    # Move-only: synthesize a price_move bullet for triage UI.
    if move_ok and not event_ok and work.daily_return is not None:
        bullets = [
            _price_move_bullet(
                ticker=work.ticker,
                list_kind=list_kind,
                daily_return=work.daily_return,
                move_sc=mscore or 2,
                held_count=held_count,
                insight_mode=mode,
                app_settings=s,
            )
        ]

    event_sev = max((b.severity for b in bullets), default=0)
    impact = max((b.impact_score for b in bullets), default=0)
    if mscore:
        from app.services.brief_impact import MOVE_SCORE_IMPACT

        impact = max(impact, MOVE_SCORE_IMPACT.get(mscore, 0))
    priority = priority_from_impact(impact)
    # Material rows always surface as at least medium when gated in.
    if priority is None:
        priority = BriefPriority.MEDIUM
    top = max(bullets, key=lambda b: b.impact_score) if bullets else None
    sentiment = top.sentiment if top else BriefSentiment.NEUTRAL
    rank = float(max(mscore or 0, event_sev, impact / 20.0))
    status = (
        BriefTickerStatus.PARTIAL
        if work.sources_partial
        else BriefTickerStatus.OK
    )
    strip = _metrics_strip(work)
    event_sev_out = event_sev if event_sev > 0 else None

    return BriefTicker(
        ticker=work.ticker,
        list_kind=list_kind,  # type: ignore[arg-type]
        status=status,
        daily_return=work.daily_return,
        move_score=mscore,
        event_severity=event_sev_out,
        rank_score=rank,
        impact_score=impact,
        priority=priority,
        sentiment=sentiment,
        headline=top.headline if top else None,
        suggested_action=top.suggested_action if top else None,
        insight=top.insight if top else None,
        bullets=bullets,
        **strip,
    )


def build_brief_summary(
    *,
    universe_count: int,
    material: list[BriefTicker],
    quiet: list[QuietTicker],
) -> BriefSummary:
    high = [t for t in material if t.priority == BriefPriority.HIGH]
    medium = [t for t in material if t.priority == BriefPriority.MEDIUM]
    pos = neg = neu = 0
    theme_counts: dict[str, int] = {}
    for t in material:
        if t.sentiment == BriefSentiment.POSITIVE:
            pos += 1
        elif t.sentiment == BriefSentiment.NEGATIVE:
            neg += 1
        else:
            neu += 1
        for b in t.bullets:
            label = theme_label(b.category)
            theme_counts[label] = theme_counts.get(label, 0) + 1

    themes = [
        k
        for k, _ in sorted(theme_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ][:6]

    if len(high) >= 3 or (len(high) >= 1 and neg >= 3):
        risk = BriefMarketRisk.HIGH
    elif len(high) >= 1 or len(medium) >= 3:
        risk = BriefMarketRisk.MEDIUM
    else:
        risk = BriefMarketRisk.LOW

    biggest_story = None
    biggest_risk = None
    biggest_opportunity = None
    if material:
        top = max(material, key=lambda t: t.impact_score)
        biggest_story = f"{top.ticker}: {top.headline or top.bullets[0].one_line_summary if top.bullets else 'Material event'}"
    risks = [t for t in material if t.sentiment == BriefSentiment.NEGATIVE]
    if risks:
        r = max(risks, key=lambda t: t.impact_score)
        biggest_risk = f"{r.ticker}: {r.headline or 'Negative event'}"
    opps = [t for t in material if t.sentiment == BriefSentiment.POSITIVE]
    if opps:
        o = max(opps, key=lambda t: t.impact_score)
        biggest_opportunity = f"{o.ticker}: {o.headline or 'Positive event'}"

    return BriefSummary(
        holdings_count=universe_count,
        high_count=len(high),
        medium_count=len(medium),
        quiet_count=len(quiet),
        positive_count=pos,
        negative_count=neg,
        neutral_count=neu,
        themes=themes,
        market_risk=risk,
        biggest_story=biggest_story,
        biggest_risk=biggest_risk,
        biggest_opportunity=biggest_opportunity,
    )


def generate_daily_brief(
    *,
    app_settings: Settings | None = None,
    force_refresh: bool = False,
    worker_fn: TickerWorkerFn | None = None,
    now: datetime | None = None,
) -> DailyBrief:
    """Sync Generate over membership snapshot; ~wall budget → partial/stale."""
    s = app_settings if app_settings is not None else default_settings
    clock = now or datetime.now(timezone.utc)
    if clock.tzinfo is None:
        clock = clock.replace(tzinfo=timezone.utc)
    insight_mode = parse_insight_mode(s.brief_insight_mode)

    membership = store.get_membership(s)
    universe = _universe(list(membership.held), list(membership.watched))
    held_count = len(membership.held)
    if not universe:
        brief = DailyBrief(
            generated_at=clock,
            window_hours=s.brief_window_hours,
            generation_status=BriefGenerationStatus.COMPLETE,
            universe_count=0,
            tickers_considered=0,
            tickers=[],
            quiet_tickers=[],
            summary=BriefSummary(holdings_count=0),
            insight_mode=insight_mode,
            empty_message=EMPTY_UNIVERSE_MSG,
            disclaimer=PHASE0_DISCLAIMER,
        )
        brief_store.save_brief(brief, app_settings=s)
        return brief

    wall = float(s.brief_generate_budget_seconds)
    workers = max(1, min(int(s.brief_max_workers), 8))
    max_tickers = int(s.brief_max_tickers)
    max_bullets = int(s.brief_max_bullets_per_ticker)
    window_hours = int(s.brief_window_hours)

    start = time.monotonic()
    results: list[TickerWorkResult] = []
    gaps: list[str] = []
    timed_out = False
    considered = 0

    def default_worker(ticker: str, list_kind: ListKind) -> TickerWorkResult:
        return _fetch_ticker_sources(
            ticker,
            list_kind,
            app_settings=s,
            force_refresh=force_refresh,
            now=clock,
            window_hours=window_hours,
        )

    worker = worker_fn or default_worker

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
                results.append(fut.result())
            except Exception as exc:  # noqa: BLE001
                gaps.append(f"{ticker}: worker failed ({exc.__class__.__name__})")
                logger.warning("brief_worker_fail ticker=%s err=%s", ticker, exc)

        if timed_out:
            for fut in futures:
                fut.cancel()
            remaining = len(universe) - considered
            if remaining > 0:
                gaps.append(
                    f"generate budget {wall:.0f}s hit; {remaining} tickers not finished"
                )

    material: list[BriefTicker] = []
    quiet: list[QuietTicker] = []
    for work in results:
        gaps.extend(work.gaps)
        row = build_ticker_row(
            work,
            max_bullets=max_bullets,
            held_count=held_count,
            insight_mode=insight_mode,
            app_settings=s,
        )
        if row is None:
            quiet.append(
                QuietTicker(ticker=work.ticker, list_kind=work.list_kind.value)  # type: ignore[arg-type]
            )
        elif row.status == BriefTickerStatus.UNAVAILABLE:
            material.append(row)
        else:
            material.append(row)

    # Tickers not finished (budget) → not in quiet (honest gap already logged).
    material.sort(
        key=lambda r: (
            r.status == BriefTickerStatus.UNAVAILABLE,
            0 if r.priority == BriefPriority.HIGH else 1,
            -r.impact_score,
            -r.rank_score,
            r.ticker,
        )
    )
    capped = material[:max_tickers]
    # Quiet = membership considered with no material row (plus not capped-out).
    capped_set = {t.ticker for t in capped}
    # Names that were material but dropped by cap become quiet? Plan: quiet =
    # no actionable events. Cap-dropped still had events — keep them out of quiet;
    # they simply aren't in the surfaced list (gap note optional).
    overflow = [t for t in material if t.ticker not in capped_set]
    if overflow:
        gaps.append(
            f"{len(overflow)} material names beyond BRIEF_MAX_TICKERS={max_tickers} not surfaced"
        )

    quiet.sort(key=lambda q: (q.list_kind != "held", q.ticker))

    if timed_out:
        gen_status = BriefGenerationStatus.PARTIAL
    elif gaps:
        gen_status = BriefGenerationStatus.PARTIAL
    else:
        gen_status = BriefGenerationStatus.COMPLETE

    if timed_out and capped:
        gen_status = BriefGenerationStatus.STALE

    empty_message = None
    if not capped:
        empty_message = EMPTY_MATERIAL_MSG

    summary = build_brief_summary(
        universe_count=len(universe),
        material=capped,
        quiet=quiet,
    )

    brief = DailyBrief(
        generated_at=clock,
        window_hours=window_hours,
        generation_status=gen_status,
        universe_count=len(universe),
        tickers_considered=considered,
        tickers=capped,
        quiet_tickers=quiet,
        summary=summary,
        insight_mode=insight_mode,
        gaps=gaps,
        empty_message=empty_message,
        disclaimer=PHASE0_DISCLAIMER,
    )
    brief_store.save_brief(brief, app_settings=s)
    logger.info(
        "brief_generated universe=%s considered=%s surfaced=%s quiet=%s status=%s mode=%s",
        len(universe),
        considered,
        len(capped),
        len(quiet),
        gen_status.value,
        insight_mode.value,
    )
    return brief


def get_latest_brief(*, app_settings: Settings | None = None) -> DailyBrief | None:
    return brief_store.get_latest_brief(app_settings)


def explain_event(
    *,
    ticker: str,
    text: str,
    category: BriefEventCategory | None = None,
    daily_return: float | None = None,
    list_kind: str = "watched",
    app_settings: Settings | None = None,
):
    """On-demand explain; returns BriefInsight."""
    s = app_settings if app_settings is not None else default_settings
    mode = parse_insight_mode(s.brief_insight_mode)
    cat = category or BriefEventCategory.OTHER_MATERIAL
    sentiment = sentiment_from_text(text, daily_return=daily_return, category=cat)
    impact = impact_from_category(cat, daily_return=daily_return)
    conf = confidence_for_event(
        category=cat, has_source_url=False, severity=3
    )
    return build_insight(
        ticker=ticker.upper(),
        category=cat,
        text=text,
        list_kind=list_kind,
        daily_return=daily_return,
        sentiment=sentiment,
        impact=impact,
        confidence=conf,
        mode=mode,
        app_settings=s,
    )

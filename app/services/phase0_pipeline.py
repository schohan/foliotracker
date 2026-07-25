"""Phase 0/1/2/2C end-to-end research pipeline."""

from __future__ import annotations

import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app.agents.report.thesis_agent import (
    DanglingCitationError,
    EmptyClaimsError,
    ThesisGenerationError,
    UncitedClaimError,
    generate_thesis,
)
from app.configs.settings import settings
from app.schemas.evidence import EvidenceConflict
from app.schemas.filings import SecFilingsBatch
from app.schemas.financials import FinancialMetrics
from app.schemas.fundamentals_minimum import (
    has_minimum_fundamentals,
    missing_minimum_fundamentals,
)
from app.schemas.news import NewsBatch
from app.schemas.phase0 import (
    PHASE0_DISCLAIMER,
    Phase0ErrorCode,
    Phase0Result,
    Phase0Status,
)
from app.schemas.ticker import InvalidTickerError, normalize_ticker
from app.services.evidence import (
    EmptyEvidenceError,
    EmptyMetricsError,
    aggregate_evidence,
    evidence_from_filings,
    evidence_from_metrics,
    evidence_from_news,
)
from app.services.merge_fundamentals import (
    ProviderSnapshot,
    merge_fundamentals,
)
from app.services.phase0_cache import cache_lookup, cache_store
from app.services.phase0_session import new_research_session
from app.services.scoring import score_from_metrics
from app.services.source_fetch import SourceRateLimitedError, cached_fetch
from app.services.source_registry import (
    SOURCE_ALPHA_VANTAGE,
    SOURCE_GOOGLE_NEWS,
    SOURCE_SEC_EDGAR,
    SOURCE_SEC_XBRL,
    SOURCE_YAHOO,
)
from app.tools.finance.alpha_vantage import (
    MissingApiKeyError as AvMissingKeyError,
    ToolParseError as AvParseError,
    ToolTimeoutError as AvTimeoutError,
    ToolUpstreamError as AvUpstreamError,
    fetch_alpha_vantage_fundamentals,
)
from app.tools.finance.yahoo_finance import (
    TickerNotFoundError,
    ToolParseError as YahooParseError,
    ToolTimeoutError as YahooTimeoutError,
    ToolUpstreamError as YahooUpstreamError,
    fetch_financial_metrics,
)
from app.tools.filings.sec_edgar import (
    TickerNotFoundError as SecTickerNotFoundError,
    ToolParseError as SecParseError,
    ToolTimeoutError as SecTimeoutError,
    ToolUpstreamError as SecUpstreamError,
    fetch_sec_filings,
)
from app.tools.filings.sec_xbrl import (
    ToolParseError as XbrlParseError,
    ToolTimeoutError as XbrlTimeoutError,
    ToolUpstreamError as XbrlUpstreamError,
    fetch_sec_xbrl_fundamentals,
)
from app.tools.news.google_news import (
    ToolParseError as NewsParseError,
    ToolTimeoutError as NewsTimeoutError,
    ToolUpstreamError as NewsUpstreamError,
    fetch_google_news,
)

logger = logging.getLogger(__name__)

_NEWS_ERRORS = (
    NewsTimeoutError,
    NewsUpstreamError,
    NewsParseError,
    SourceRateLimitedError,
)
_SEC_ERRORS = (
    SecTimeoutError,
    SecUpstreamError,
    SecParseError,
    SecTickerNotFoundError,
    SourceRateLimitedError,
)
_XBRL_ERRORS = (
    XbrlTimeoutError,
    XbrlUpstreamError,
    XbrlParseError,
    SecTickerNotFoundError,
    SourceRateLimitedError,
)
_YAHOO_ERRORS = (
    YahooTimeoutError,
    YahooUpstreamError,
    TickerNotFoundError,
    YahooParseError,
    InvalidTickerError,
    SourceRateLimitedError,
)
_AV_ERRORS = (
    AvTimeoutError,
    AvUpstreamError,
    AvParseError,
    AvMissingKeyError,
    SourceRateLimitedError,
)


def _error_result(
    ticker: str,
    request_id: str,
    message: str,
    *,
    error_code: str | None = None,
    cache_hit: bool = False,
) -> Phase0Result:
    return Phase0Result(
        ticker=ticker or "UNKNOWN",
        status=Phase0Status.ERROR,
        evidence=None,
        thesis=None,
        error_message=message,
        error_code=error_code,
        disclaimer=PHASE0_DISCLAIMER,
        cache_hit=cache_hit,
        request_id=request_id,
    )


def _thesis_user_message(
    ticker: str,
    request_id: str,
    code: Phase0ErrorCode,
) -> str:
    """Human-readable thesis-stage failure (no exception class names)."""
    if code == Phase0ErrorCode.THESIS_EMPTY_CLAIMS:
        detail = (
            "could not produce a cited investment thesis "
            "(no material claims after one repair attempt)"
        )
    elif code == Phase0ErrorCode.THESIS_DANGLING_CITATION:
        detail = (
            "the investment thesis cited evidence ids that are not in the "
            "bundle after one repair attempt"
        )
    elif code == Phase0ErrorCode.THESIS_UNCITED:
        detail = (
            "the investment thesis had material claims without valid "
            "evidence citations after one repair attempt"
        )
    else:
        detail = "could not generate an investment thesis"
    return (
        f"We gathered evidence for {ticker} but {detail}. "
        f"Evidence is included; thesis was withheld. "
        f"Reference request_id {request_id}."
    )


def _map_thesis_error(exc: Exception) -> Phase0ErrorCode:
    code = getattr(exc, "error_code", None)
    if isinstance(code, Phase0ErrorCode):
        return code
    if isinstance(exc, EmptyClaimsError):
        return Phase0ErrorCode.THESIS_EMPTY_CLAIMS
    if isinstance(exc, UncitedClaimError):
        return Phase0ErrorCode.THESIS_UNCITED
    if isinstance(exc, DanglingCitationError):
        return Phase0ErrorCode.THESIS_DANGLING_CITATION
    return Phase0ErrorCode.THESIS_GENERATION_FAILED


def _fundamentals_conflicts_as_evidence(
    conflicts: list[Any],
) -> list[EvidenceConflict]:
    """Map merge field conflicts into EvidenceConflict records."""
    out: list[EvidenceConflict] = []
    for i, c in enumerate(conflicts):
        sources = ", ".join(sorted(c.values.keys()))
        out.append(
            EvidenceConflict(
                id=f"conflict_fundamentals_{i}_{c.field_path}",
                topic="fundamentals_field",
                item_ids=[],
                summary=(
                    f"Field {c.field_path} disagreed across {sources}; "
                    f"kept {c.chosen_source_id}"
                ),
                severity="warn",
            )
        )
    return out


def run_phase0_research(
    ticker: str,
    *,
    session_state: dict[str, Any] | None = None,
    skip_cache: bool = False,
    model_caller: Any | None = None,
) -> Phase0Result:
    """Run research: validate → result-cache → source-cached fan-out → merge → evidence → score → thesis.

    Pure orchestration; safe to expose as an ADK tool.
    Phase 2C: Yahoo + news + SEC filings + SEC XBRL + optional Alpha Vantage;
    merge fundamentals; Yahoo failure softens to partial when
    ``has_minimum_fundamentals``. AV fills forward/market gaps when keyed.
    """
    request_id = str(uuid.uuid4())
    started = time.perf_counter()

    try:
        normalized = normalize_ticker(ticker)
    except InvalidTickerError as exc:
        logger.info("pipeline_reject request_id=%s err=%s", request_id, exc)
        return _error_result(
            "INVALID",
            request_id,
            str(exc),
            error_code=Phase0ErrorCode.INVALID_TICKER.value,
        )

    state = new_research_session(session_state or {}, normalized)
    logger.info(
        "pipeline_start request_id=%s ticker=%s",
        request_id,
        normalized,
    )

    if not skip_cache:
        hit = cache_lookup(
            normalized,
            cache_dir=settings.phase0_cache_dir,
            ttl_seconds=settings.phase0_cache_ttl_seconds,
        )
        if hit is not None:
            hit = hit.model_copy(update={"request_id": request_id, "cache_hit": True})
            logger.info(
                "pipeline_end request_id=%s ticker=%s status=%s cache_hit=true latency_ms=%.0f",
                request_id,
                normalized,
                hit.status.value,
                (time.perf_counter() - started) * 1000,
            )
            return hit

    news_failed = False
    sec_failed = False
    xbrl_failed = False
    yahoo_failed = False
    av_failed = False
    news_batch = None
    filings_batch = None
    yahoo_metrics: FinancialMetrics | None = None
    xbrl_metrics: FinancialMetrics | None = None
    av_metrics: FinancialMetrics | None = None
    av_enabled = bool(settings.alpha_vantage_api_key)

    def _fetch_yahoo() -> FinancialMetrics:
        result = cached_fetch(
            SOURCE_YAHOO,
            normalized,
            lambda: fetch_financial_metrics(normalized),
            FinancialMetrics,
            app_settings=settings,
        )
        return result.data

    def _fetch_news() -> NewsBatch:
        result = cached_fetch(
            SOURCE_GOOGLE_NEWS,
            normalized,
            lambda: fetch_google_news(normalized),
            NewsBatch,
            app_settings=settings,
        )
        return result.data

    def _fetch_sec() -> SecFilingsBatch:
        result = cached_fetch(
            SOURCE_SEC_EDGAR,
            normalized,
            lambda: fetch_sec_filings(normalized),
            SecFilingsBatch,
            app_settings=settings,
        )
        return result.data

    def _fetch_xbrl() -> FinancialMetrics:
        result = cached_fetch(
            SOURCE_SEC_XBRL,
            normalized,
            lambda: fetch_sec_xbrl_fundamentals(normalized),
            FinancialMetrics,
            app_settings=settings,
        )
        return result.data

    def _fetch_av() -> FinancialMetrics:
        result = cached_fetch(
            SOURCE_ALPHA_VANTAGE,
            normalized,
            lambda: fetch_alpha_vantage_fundamentals(normalized),
            FinancialMetrics,
            app_settings=settings,
        )
        return result.data

    with ThreadPoolExecutor(max_workers=5) as pool:
        fut_yahoo = pool.submit(_fetch_yahoo)
        fut_news = pool.submit(_fetch_news)
        fut_sec = pool.submit(_fetch_sec)
        fut_xbrl = pool.submit(_fetch_xbrl)
        fut_av = pool.submit(_fetch_av) if av_enabled else None

        try:
            yahoo_metrics = fut_yahoo.result()
        except _YAHOO_ERRORS as exc:
            yahoo_failed = True
            logger.warning(
                "yahoo_failed request_id=%s ticker=%s err=%s",
                request_id,
                normalized,
                exc,
            )

        try:
            news_batch = fut_news.result()
        except _NEWS_ERRORS as exc:
            news_failed = True
            logger.warning(
                "news_failed request_id=%s ticker=%s err=%s",
                request_id,
                normalized,
                exc,
            )

        try:
            filings_batch = fut_sec.result()
        except _SEC_ERRORS as exc:
            sec_failed = True
            logger.warning(
                "sec_failed request_id=%s ticker=%s err=%s",
                request_id,
                normalized,
                exc,
            )

        try:
            xbrl_metrics = fut_xbrl.result()
        except _XBRL_ERRORS as exc:
            xbrl_failed = True
            logger.warning(
                "xbrl_failed request_id=%s ticker=%s err=%s",
                request_id,
                normalized,
                exc,
            )

        if fut_av is not None:
            try:
                av_metrics = fut_av.result()
            except _AV_ERRORS as exc:
                av_failed = True
                logger.warning(
                    "alpha_vantage_failed request_id=%s ticker=%s err=%s",
                    request_id,
                    normalized,
                    exc,
                )

    providers: list[ProviderSnapshot | None] = []
    if yahoo_metrics is not None:
        providers.append(
            ProviderSnapshot(source_id=SOURCE_YAHOO, snapshot=yahoo_metrics)
        )
    if xbrl_metrics is not None:
        providers.append(
            ProviderSnapshot(source_id=SOURCE_SEC_XBRL, snapshot=xbrl_metrics)
        )
    if av_metrics is not None:
        providers.append(
            ProviderSnapshot(source_id=SOURCE_ALPHA_VANTAGE, snapshot=av_metrics)
        )

    merge_result = merge_fundamentals(providers, ticker=normalized)
    metrics = merge_result.snapshot

    # Soften Yahoo-fatal only when merge satisfies the locked min field set.
    # Yahoo success keeps prior behavior (partial metrics via evidence rules).
    if yahoo_metrics is None and xbrl_metrics is None:
        result = _error_result(
            normalized,
            request_id,
            "DATA_FETCH_FAILED: no Yahoo or SEC XBRL fundamentals",
            error_code=Phase0ErrorCode.DATA_FETCH_FAILED.value,
        )
        logger.info(
            "pipeline_end request_id=%s ticker=%s status=error "
            "error_code=%s yahoo_failed=%s xbrl_failed=%s latency_ms=%.0f",
            request_id,
            normalized,
            result.error_code,
            yahoo_failed,
            xbrl_failed,
            (time.perf_counter() - started) * 1000,
        )
        return result

    if yahoo_failed and not has_minimum_fundamentals(metrics):
        missing = missing_minimum_fundamentals(metrics)
        msg = (
            f"Yahoo failed and merged fundamentals below minimum set "
            f"(missing={missing[:8]})"
        )
        result = _error_result(
            normalized,
            request_id,
            msg,
            error_code=Phase0ErrorCode.DATA_FETCH_FAILED.value,
        )
        logger.info(
            "pipeline_end request_id=%s ticker=%s status=error "
            "error_code=%s yahoo_failed=true missing=%s latency_ms=%.0f",
            request_id,
            normalized,
            result.error_code,
            missing[:8],
            (time.perf_counter() - started) * 1000,
        )
        return result

    state["financial_metrics"] = metrics.model_dump(mode="json")
    state["fundamentals"] = metrics.model_dump(mode="json")
    if news_batch is not None:
        state["news_batch"] = news_batch.model_dump(mode="json")
    if filings_batch is not None:
        state["filings_batch"] = filings_batch.model_dump(mode="json")

    try:
        evidence_items = [evidence_from_metrics(metrics)]
        if news_batch is not None:
            evidence_items.extend(evidence_from_news(news_batch))
        if filings_batch is not None:
            evidence_items.extend(evidence_from_filings(filings_batch))
        bundle = aggregate_evidence(
            normalized,
            evidence_items,
            news_failed=news_failed,
            # Filings metadata gap only; XBRL is fundamentals (merged separately).
            sec_failed=sec_failed,
        )
        if merge_result.conflicts:
            extra = _fundamentals_conflicts_as_evidence(merge_result.conflicts)
            bundle = bundle.model_copy(
                update={"conflicts": list(bundle.conflicts) + extra}
            )
            from app.schemas.evidence import BundleStatus

            if bundle.status == BundleStatus.OK:
                bundle = bundle.model_copy(update={"status": BundleStatus.PARTIAL})
        state["evidence_bundle"] = bundle.model_dump(mode="json")
    except (EmptyMetricsError, EmptyEvidenceError) as exc:
        result = _error_result(
            normalized,
            request_id,
            f"{type(exc).__name__}: {exc}",
            error_code=Phase0ErrorCode.EMPTY_EVIDENCE.value,
        )
        return result

    scorecard = score_from_metrics(metrics)
    if scorecard is not None:
        state["scorecard"] = scorecard.model_dump(mode="json")

    status = (
        Phase0Status.PARTIAL
        if bundle.status.value == "partial" or yahoo_failed
        else Phase0Status.OK
    )

    try:
        thesis = generate_thesis(bundle, model_caller=model_caller)
        state["thesis"] = thesis.model_dump(mode="json")
    except (
        EmptyClaimsError,
        UncitedClaimError,
        DanglingCitationError,
        ThesisGenerationError,
    ) as exc:
        code = _map_thesis_error(exc)
        result = _error_result(
            normalized,
            request_id,
            _thesis_user_message(normalized, request_id, code),
            error_code=code.value,
        )
        result = result.model_copy(
            update={
                "evidence": bundle,
                "scorecard": scorecard,
                "fundamentals": metrics,
            }
        )
        logger.info(
            "pipeline_end request_id=%s ticker=%s status=error stage=thesis "
            "error_code=%s exc_type=%s latency_ms=%.0f",
            request_id,
            normalized,
            code.value,
            type(exc).__name__,
            (time.perf_counter() - started) * 1000,
        )
        return result

    result = Phase0Result(
        ticker=normalized,
        status=status,
        evidence=bundle,
        thesis=thesis,
        scorecard=scorecard,
        fundamentals=metrics,
        error_message=None,
        error_code=None,
        disclaimer=PHASE0_DISCLAIMER,
        cache_hit=False,
        request_id=request_id,
    )
    cache_store(result, cache_dir=settings.phase0_cache_dir)
    state["phase0_status"] = status.value
    state["cache_hit"] = False

    logger.info(
        "pipeline_end request_id=%s ticker=%s status=%s cache_hit=false "
        "conflicts=%s yahoo_failed=%s xbrl_failed=%s av_failed=%s latency_ms=%.0f",
        request_id,
        normalized,
        status.value,
        len(bundle.conflicts),
        yahoo_failed,
        xbrl_failed,
        av_failed,
        (time.perf_counter() - started) * 1000,
    )
    return result

"""Phase 0/1/2 end-to-end research pipeline."""

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
from app.services.phase0_cache import cache_lookup, cache_store
from app.services.phase0_session import new_research_session
from app.services.scoring import score_from_metrics
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
from app.tools.news.google_news import (
    ToolParseError as NewsParseError,
    ToolTimeoutError as NewsTimeoutError,
    ToolUpstreamError as NewsUpstreamError,
    fetch_google_news,
)

logger = logging.getLogger(__name__)

_NEWS_ERRORS = (NewsTimeoutError, NewsUpstreamError, NewsParseError)
_SEC_ERRORS = (
    SecTimeoutError,
    SecUpstreamError,
    SecParseError,
    SecTickerNotFoundError,
)
_YAHOO_ERRORS = (
    YahooTimeoutError,
    YahooUpstreamError,
    TickerNotFoundError,
    YahooParseError,
    InvalidTickerError,
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


def run_phase0_research(
    ticker: str,
    *,
    session_state: dict[str, Any] | None = None,
    skip_cache: bool = False,
    model_caller: Any | None = None,
) -> Phase0Result:
    """Run research: validate → cache → yahoo+news+sec → evidence → score → thesis → cache.

    Pure orchestration; safe to expose as an ADK tool.
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
            # Preserve pipeline request logging correlation: overwrite with this request_id
            hit = hit.model_copy(update={"request_id": request_id, "cache_hit": True})
            logger.info(
                "pipeline_end request_id=%s ticker=%s status=%s cache_hit=true latency_ms=%.0f",
                request_id,
                normalized,
                hit.status.value,
                (time.perf_counter() - started) * 1000,
            )
            return hit

    # Fan out Yahoo + news + SEC; Yahoo failure is fatal; news/SEC failure → partial
    news_failed = False
    sec_failed = False
    news_batch = None
    filings_batch = None
    try:
        with ThreadPoolExecutor(max_workers=3) as pool:
            fut_yahoo = pool.submit(fetch_financial_metrics, normalized)
            fut_news = pool.submit(fetch_google_news, normalized)
            fut_sec = pool.submit(fetch_sec_filings, normalized)
            try:
                metrics = fut_yahoo.result()
            except _YAHOO_ERRORS as exc:
                fut_news.cancel()
                fut_sec.cancel()
                result = _error_result(
                    normalized,
                    request_id,
                    f"{type(exc).__name__}: {exc}",
                    error_code=Phase0ErrorCode.DATA_FETCH_FAILED.value,
                )
                logger.info(
                    "pipeline_end request_id=%s ticker=%s status=error "
                    "error_code=%s latency_ms=%.0f",
                    request_id,
                    normalized,
                    result.error_code,
                    (time.perf_counter() - started) * 1000,
                )
                return result

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
    except _YAHOO_ERRORS as exc:
        result = _error_result(
            normalized,
            request_id,
            f"{type(exc).__name__}: {exc}",
            error_code=Phase0ErrorCode.DATA_FETCH_FAILED.value,
        )
        logger.info(
            "pipeline_end request_id=%s ticker=%s status=error "
            "error_code=%s latency_ms=%.0f",
            request_id,
            normalized,
            result.error_code,
            (time.perf_counter() - started) * 1000,
        )
        return result

    state["financial_metrics"] = metrics.model_dump()
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
            sec_failed=sec_failed,
        )
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
        if bundle.status.value == "partial"
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
        # Still attach evidence + scorecard for debuggability on thesis failure
        result = result.model_copy(
            update={"evidence": bundle, "scorecard": scorecard}
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
        "conflicts=%s latency_ms=%.0f",
        request_id,
        normalized,
        status.value,
        len(bundle.conflicts),
        (time.perf_counter() - started) * 1000,
    )
    return result

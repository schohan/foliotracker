"""Phase 0 end-to-end research pipeline."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from app.agents.report.thesis_agent import (
    DanglingCitationError,
    ThesisGenerationError,
    UncitedClaimError,
    generate_thesis,
)
from app.configs.settings import settings
from app.schemas.phase0 import PHASE0_DISCLAIMER, Phase0Result, Phase0Status
from app.schemas.ticker import InvalidTickerError, normalize_ticker
from app.services.evidence import (
    EmptyEvidenceError,
    EmptyMetricsError,
    aggregate_evidence,
    evidence_from_metrics,
)
from app.services.phase0_cache import cache_lookup, cache_store
from app.services.phase0_session import new_research_session
from app.tools.finance.yahoo_finance import (
    TickerNotFoundError,
    ToolParseError,
    ToolTimeoutError,
    ToolUpstreamError,
    fetch_financial_metrics,
)

logger = logging.getLogger(__name__)


def _error_result(
    ticker: str,
    request_id: str,
    message: str,
    *,
    cache_hit: bool = False,
) -> Phase0Result:
    return Phase0Result(
        ticker=ticker or "UNKNOWN",
        status=Phase0Status.ERROR,
        evidence=None,
        thesis=None,
        error_message=message,
        disclaimer=PHASE0_DISCLAIMER,
        cache_hit=cache_hit,
        request_id=request_id,
    )


def run_phase0_research(
    ticker: str,
    *,
    session_state: dict[str, Any] | None = None,
    skip_cache: bool = False,
    model_caller: Any | None = None,
) -> Phase0Result:
    """Run Phase 0: validate → cache → yahoo → evidence → thesis → cache store.

    Pure orchestration; safe to expose as an ADK tool.
    """
    request_id = str(uuid.uuid4())
    started = time.perf_counter()

    try:
        normalized = normalize_ticker(ticker)
    except InvalidTickerError as exc:
        logger.info("pipeline_reject request_id=%s err=%s", request_id, exc)
        return _error_result("INVALID", request_id, str(exc))

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

    try:
        metrics = fetch_financial_metrics(normalized)
        state["financial_metrics"] = metrics.model_dump()
    except (
        ToolTimeoutError,
        ToolUpstreamError,
        TickerNotFoundError,
        ToolParseError,
        InvalidTickerError,
    ) as exc:
        result = _error_result(normalized, request_id, f"{type(exc).__name__}: {exc}")
        logger.info(
            "pipeline_end request_id=%s ticker=%s status=error latency_ms=%.0f",
            request_id,
            normalized,
            (time.perf_counter() - started) * 1000,
        )
        return result

    try:
        evidence = evidence_from_metrics(metrics)
        bundle = aggregate_evidence(normalized, [evidence])
        state["evidence_bundle"] = bundle.model_dump(mode="json")
    except (EmptyMetricsError, EmptyEvidenceError) as exc:
        result = _error_result(normalized, request_id, f"{type(exc).__name__}: {exc}")
        return result

    status = (
        Phase0Status.PARTIAL
        if bundle.status.value == "partial"
        else Phase0Status.OK
    )

    try:
        thesis = generate_thesis(bundle, model_caller=model_caller)
        state["thesis"] = thesis.model_dump(mode="json")
    except (UncitedClaimError, DanglingCitationError, ThesisGenerationError) as exc:
        result = _error_result(
            normalized,
            request_id,
            f"{type(exc).__name__}: {exc}",
        )
        # Still attach evidence for debuggability on thesis failure
        result = result.model_copy(update={"evidence": bundle})
        logger.info(
            "pipeline_end request_id=%s ticker=%s status=error stage=thesis latency_ms=%.0f",
            request_id,
            normalized,
            (time.perf_counter() - started) * 1000,
        )
        return result

    result = Phase0Result(
        ticker=normalized,
        status=status,
        evidence=bundle,
        thesis=thesis,
        error_message=None,
        disclaimer=PHASE0_DISCLAIMER,
        cache_hit=False,
        request_id=request_id,
    )
    cache_store(result, cache_dir=settings.phase0_cache_dir)
    state["phase0_status"] = status.value
    state["cache_hit"] = False

    logger.info(
        "pipeline_end request_id=%s ticker=%s status=%s cache_hit=false latency_ms=%.0f",
        request_id,
        normalized,
        status.value,
        (time.perf_counter() - started) * 1000,
    )
    return result

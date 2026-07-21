"""Evidence builders — pure Python, no LLM."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone

from app.schemas.evidence import BundleStatus, Evidence, EvidenceBundle
from app.schemas.financials import FinancialMetrics

logger = logging.getLogger(__name__)

YAHOO_SOURCE = "Yahoo Finance"
YAHOO_CONFIDENCE = 0.95


class EmptyMetricsError(ValueError):
    """All numeric metric fields are null/missing."""


class EmptyEvidenceError(ValueError):
    """Aggregator received no evidence items."""


def _metric_fields(metrics: FinancialMetrics) -> dict:
    return {
        "ticker": metrics.ticker,
        "market_cap": metrics.market_cap,
        "revenue_growth": metrics.revenue_growth,
        "gross_margin": metrics.gross_margin,
        "operating_margin": metrics.operating_margin,
        "free_cash_flow": metrics.free_cash_flow,
        "debt_to_equity": metrics.debt_to_equity,
        "pe_ratio": metrics.pe_ratio,
    }


def _has_any_metric(metrics: FinancialMetrics) -> bool:
    return any(
        getattr(metrics, field) is not None
        for field in (
            "market_cap",
            "revenue_growth",
            "gross_margin",
            "operating_margin",
            "free_cash_flow",
            "debt_to_equity",
            "pe_ratio",
        )
    )


def evidence_id_for(ticker: str, data: dict) -> str:
    digest = hashlib.sha256(
        repr(sorted((k, v) for k, v in data.items())).encode("utf-8")
    ).hexdigest()[:10]
    return f"ev_financial_{ticker}_{digest}"


def evidence_from_metrics(metrics: FinancialMetrics) -> Evidence:
    """Convert FinancialMetrics into a single financial Evidence item."""
    if not _has_any_metric(metrics):
        raise EmptyMetricsError(f"no numeric metrics for {metrics.ticker}")

    data = _metric_fields(metrics)
    eid = evidence_id_for(metrics.ticker, data)
    return Evidence(
        id=eid,
        type="financial",
        source=YAHOO_SOURCE,
        confidence=YAHOO_CONFIDENCE,
        timestamp=datetime.now(timezone.utc),
        citation=f"https://finance.yahoo.com/quote/{metrics.ticker}",
        data=data,
    )


def aggregate_evidence(ticker: str, items: list[Evidence]) -> EvidenceBundle:
    """Pass-through aggregator — assigns bundle status, no cross-source merge."""
    if not items:
        raise EmptyEvidenceError(f"no evidence for {ticker}")

    # partial if any financial item has mostly nulls in data
    partial = False
    for item in items:
        if item.type == "financial":
            values = [
                v
                for k, v in item.data.items()
                if k != "ticker"
            ]
            if values and all(v is None for v in values):
                partial = True
            elif values and any(v is None for v in values):
                partial = True

    status = BundleStatus.PARTIAL if partial else BundleStatus.OK
    logger.info(
        "aggregate_ok ticker=%s items=%s status=%s",
        ticker,
        len(items),
        status.value,
    )
    return EvidenceBundle(ticker=ticker, items=list(items), status=status)

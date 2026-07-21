"""Evidence from metrics + pass-through aggregator."""

from __future__ import annotations

import pytest

from app.schemas.evidence import BundleStatus, Evidence
from app.schemas.financials import FinancialMetrics
from app.services.evidence import (
    EmptyEvidenceError,
    EmptyMetricsError,
    aggregate_evidence,
    evidence_from_metrics,
)


def test_evidence_from_metrics_assigns_stable_id_and_yahoo_fields() -> None:
    metrics = FinancialMetrics(
        ticker="NVDA",
        market_cap=1.0e12,
        revenue_growth=0.18,
        pe_ratio=30.0,
    )
    ev = evidence_from_metrics(metrics)
    assert isinstance(ev, Evidence)
    assert ev.id.startswith("ev_financial_NVDA")
    assert ev.type == "financial"
    assert ev.source == "Yahoo Finance"
    assert ev.confidence == 0.95
    assert ev.data["revenue_growth"] == 0.18


def test_evidence_from_metrics_all_null_raises_empty_metrics() -> None:
    metrics = FinancialMetrics(ticker="NVDA")
    with pytest.raises(EmptyMetricsError):
        evidence_from_metrics(metrics)


def test_aggregator_pass_through_bundle() -> None:
    metrics = FinancialMetrics(ticker="NVDA", revenue_growth=0.1, pe_ratio=20.0)
    ev = evidence_from_metrics(metrics)
    bundle = aggregate_evidence("NVDA", [ev])
    assert bundle.ticker == "NVDA"
    assert len(bundle.items) == 1
    assert isinstance(bundle.items[0], Evidence)
    assert bundle.status in (BundleStatus.OK, BundleStatus.PARTIAL)


def test_aggregator_empty_list_raises() -> None:
    with pytest.raises(EmptyEvidenceError):
        aggregate_evidence("NVDA", [])

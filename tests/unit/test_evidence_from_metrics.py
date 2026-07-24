"""Evidence from metrics/news + aggregator merge/conflict tests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.schemas.evidence import BundleStatus, Evidence
from app.schemas.financials import FinancialMetrics
from app.schemas.news import NewsArticle, NewsBatch
from app.services.evidence import (
    EmptyEvidenceError,
    EmptyMetricsError,
    aggregate_evidence,
    evidence_from_metrics,
    evidence_from_news,
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


def test_evidence_from_news_stable_ids() -> None:
    batch = NewsBatch(
        ticker="NVDA",
        articles=[
            NewsArticle(
                title="NVDA beats estimates",
                url="https://example.com/a",
                published_at=datetime(2026, 7, 20, tzinfo=timezone.utc),
                publisher="Wire",
            )
        ],
    )
    items = evidence_from_news(batch)
    assert len(items) == 1
    assert items[0].id.startswith("ev_news_NVDA_")
    assert items[0].type == "news"
    assert items[0].source == "Google News"
    assert items[0].confidence == 0.7
    assert items[0].citation == "https://example.com/a"
    assert items[0].data["title"] == "NVDA beats estimates"


def test_aggregator_multi_source_ok_when_aligned() -> None:
    metrics = FinancialMetrics(
        ticker="NVDA",
        market_cap=1e12,
        revenue_growth=0.18,
        pe_ratio=40.0,
        gross_margin=0.7,
        operating_margin=0.5,
        free_cash_flow=1e10,
        debt_to_equity=0.2,
    )
    fin = evidence_from_metrics(metrics)
    news = evidence_from_news(
        NewsBatch(
            ticker="NVDA",
            articles=[
                NewsArticle(
                    title="NVDA growth continues as AI demand stays strong",
                    url="https://example.com/pos",
                    published_at=datetime(2026, 7, 20, tzinfo=timezone.utc),
                )
            ],
        )
    )
    bundle = aggregate_evidence("NVDA", [fin, *news])
    assert bundle.ticker == "NVDA"
    assert len(bundle.items) >= 2
    assert bundle.status == BundleStatus.OK
    assert bundle.conflicts == []


def test_aggregator_dedupes_same_citation() -> None:
    a = Evidence(
        id="ev_news_NVDA_a",
        type="news",
        source="Google News",
        confidence=0.7,
        citation="https://example.com/same",
        data={"title": "One title", "ticker": "NVDA"},
    )
    b = Evidence(
        id="ev_news_NVDA_b",
        type="news",
        source="Google News",
        confidence=0.8,
        citation="https://example.com/same",
        data={"title": "Other title", "ticker": "NVDA"},
    )
    fin = evidence_from_metrics(
        FinancialMetrics(ticker="NVDA", revenue_growth=0.1, pe_ratio=20.0)
    )
    bundle = aggregate_evidence("NVDA", [fin, a, b])
    news_items = [i for i in bundle.items if i.type == "news"]
    assert len(news_items) == 1
    assert news_items[0].id == "ev_news_NVDA_b"


def test_aggregator_caps_news() -> None:
    fin = evidence_from_metrics(
        FinancialMetrics(ticker="NVDA", revenue_growth=0.1, pe_ratio=20.0)
    )
    articles = [
        NewsArticle(
            title=f"Headline {i}",
            url=f"https://example.com/{i}",
            published_at=datetime(2026, 7, i + 1, tzinfo=timezone.utc),
        )
        for i in range(8)
    ]
    news = evidence_from_news(NewsBatch(ticker="NVDA", articles=articles))
    bundle = aggregate_evidence("NVDA", [fin, *news], max_news_articles=5)
    assert len([i for i in bundle.items if i.type == "news"]) == 5


def test_aggregator_conflict_headline_tone() -> None:
    fin = evidence_from_metrics(
        FinancialMetrics(
            ticker="NVDA",
            revenue_growth=0.1,
            pe_ratio=20.0,
            gross_margin=0.5,
            market_cap=1e12,
            operating_margin=0.3,
            free_cash_flow=1e9,
            debt_to_equity=0.1,
        )
    )
    news = evidence_from_news(
        NewsBatch(
            ticker="NVDA",
            articles=[
                NewsArticle(
                    title="NVDA stock surges on strong demand",
                    url="https://example.com/pos",
                ),
                NewsArticle(
                    title="NVDA plunges after guidance cut",
                    url="https://example.com/neg",
                ),
            ],
        )
    )
    bundle = aggregate_evidence("NVDA", [fin, *news])
    assert bundle.status == BundleStatus.PARTIAL
    assert any(c.topic == "headline_tone" for c in bundle.conflicts)
    known = {i.id for i in bundle.items}
    for c in bundle.conflicts:
        assert set(c.item_ids) <= known


def test_aggregator_news_failed_marks_partial() -> None:
    fin = evidence_from_metrics(
        FinancialMetrics(
            ticker="NVDA",
            revenue_growth=0.1,
            pe_ratio=20.0,
            gross_margin=0.5,
            market_cap=1e12,
            operating_margin=0.3,
            free_cash_flow=1e9,
            debt_to_equity=0.1,
        )
    )
    bundle = aggregate_evidence("NVDA", [fin], news_failed=True)
    assert bundle.status == BundleStatus.PARTIAL
    assert len(bundle.items) == 1


def test_aggregator_empty_list_raises() -> None:
    with pytest.raises(EmptyEvidenceError):
        aggregate_evidence("NVDA", [])

"""Brief keyword / SEC classification."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.schemas.brief import BriefEventCategory
from app.schemas.evidence import Evidence
from app.services.brief_classify import (
    CATEGORY_SEVERITY,
    classify_evidence,
    classify_headline,
    classify_sec_form,
)


def test_classify_headline_categories() -> None:
    assert classify_headline("Company raises guidance after earnings") == (
        BriefEventCategory.EARNINGS_GUIDANCE
    )
    assert classify_headline("Firm hit by ransomware attack") == (
        BriefEventCategory.SECURITY_BREACH
    )
    assert classify_headline("Analyst upgrade, new price target") == (
        BriefEventCategory.ANALYST_RATING
    )
    assert classify_headline("Unrelated weather story") is None


def test_classify_sec_8k() -> None:
    assert classify_sec_form("8-K") == BriefEventCategory.OTHER_MATERIAL
    assert classify_sec_form("10-K") is None


def test_classify_evidence_window_and_rank() -> None:
    now = datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc)
    items = [
        Evidence(
            id="ev_news_a",
            type="news",
            source="Google News",
            confidence=0.7,
            citation="https://example.com/a",
            data={
                "title": "Analyst upgrade lifts shares",
                "published_at": (now - timedelta(hours=2)).isoformat(),
                "url": "https://example.com/a",
            },
        ),
        Evidence(
            id="ev_news_old",
            type="news",
            source="Google News",
            confidence=0.7,
            citation="https://example.com/old",
            data={
                "title": "Analyst upgrade last week",
                "published_at": (now - timedelta(days=3)).isoformat(),
                "url": "https://example.com/old",
            },
        ),
        Evidence(
            id="ev_sec_b",
            type="sec",
            source="SEC EDGAR",
            confidence=0.9,
            citation="https://sec.gov/b",
            data={
                "form": "8-K",
                "title": "8-K filed today",
                "filing_date": now.date().isoformat(),
                "url": "https://sec.gov/b",
            },
        ),
    ]
    events = classify_evidence(items, now=now, window_hours=24)
    assert len(events) == 2
    # 8-K other_material severity 2; analyst 3 — analyst first
    assert events[0].category == BriefEventCategory.ANALYST_RATING
    assert events[0].severity == CATEGORY_SEVERITY[BriefEventCategory.ANALYST_RATING]
    assert events[1].category == BriefEventCategory.OTHER_MATERIAL

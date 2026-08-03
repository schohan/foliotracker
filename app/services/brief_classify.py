"""Deterministic Brief event classification (keyword + SEC form heuristics)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

from app.schemas.brief import BriefEventCategory
from app.schemas.evidence import Evidence

# Design severity table (unit-tested).
CATEGORY_SEVERITY: dict[BriefEventCategory, int] = {
    BriefEventCategory.EARNINGS_GUIDANCE: 5,
    BriefEventCategory.SECURITY_BREACH: 5,
    BriefEventCategory.CONTRACTS_WON_LOST: 4,
    BriefEventCategory.REGULATORY_MATERIAL: 4,
    BriefEventCategory.ANALYST_RATING: 3,
    BriefEventCategory.PRODUCT_ANNOUNCEMENT: 3,
    BriefEventCategory.OTHER_MATERIAL: 2,
    BriefEventCategory.PRICE_MOVE: 2,
}

# Ordered: first match wins (higher-severity categories first).
_KEYWORD_RULES: list[tuple[BriefEventCategory, tuple[str, ...]]] = [
    (
        BriefEventCategory.SECURITY_BREACH,
        (
            "data breach",
            "cyberattack",
            "cyber attack",
            "ransomware",
            "hacked",
            "security breach",
            "security incident",
        ),
    ),
    (
        BriefEventCategory.EARNINGS_GUIDANCE,
        (
            "earnings",
            "guidance",
            "outlook",
            "eps",
            "quarterly results",
            "q1 results",
            "q2 results",
            "q3 results",
            "q4 results",
            "beats estimates",
            "misses estimates",
            "raises forecast",
            "cuts forecast",
            "profit warning",
        ),
    ),
    (
        BriefEventCategory.CONTRACTS_WON_LOST,
        (
            "wins contract",
            "won contract",
            "loses contract",
            "lost contract",
            "awarded contract",
            "multi-year deal",
            "supply agreement",
            "partnership deal",
        ),
    ),
    (
        BriefEventCategory.REGULATORY_MATERIAL,
        (
            "sec investigation",
            "doj",
            "antitrust",
            "fda",
            "regulatory",
            "lawsuit",
            "sued",
            "settlement",
            "fine",
            "sanction",
            "probe",
            "subpoena",
        ),
    ),
    (
        BriefEventCategory.ANALYST_RATING,
        (
            "upgrade",
            "downgrade",
            "price target",
            "initiates coverage",
            "raises target",
            "cuts target",
            "overweight",
            "underweight",
            "buy rating",
            "sell rating",
        ),
    ),
    (
        BriefEventCategory.PRODUCT_ANNOUNCEMENT,
        (
            "launches",
            "unveils",
            "announces product",
            "new product",
            "product launch",
            "release",
            "rollout",
        ),
    ),
]

# SEC forms treated as material in the rolling window without keyword match.
_MATERIAL_SEC_FORMS = frozenset({"8-K", "8-K/A", "6-K", "SC 13D", "SC 13G", "4"})


@dataclass(frozen=True)
class ClassifiedEvent:
    category: BriefEventCategory
    severity: int
    evidence: Evidence
    title: str
    source_url: str | None
    published_at: datetime | None


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def classify_headline(title: str) -> BriefEventCategory | None:
    """Return category for a headline, or None if no keyword hit."""
    norm = _normalize(title)
    if not norm:
        return None
    for category, phrases in _KEYWORD_RULES:
        for phrase in phrases:
            if phrase in norm:
                return category
    return None


def classify_sec_form(form: str | None) -> BriefEventCategory | None:
    if not form:
        return None
    f = form.strip().upper()
    if f in _MATERIAL_SEC_FORMS or f.startswith("8-K"):
        return BriefEventCategory.OTHER_MATERIAL
    return None


def _evidence_title(ev: Evidence) -> str:
    data = ev.data or {}
    title = data.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    if ev.type == "sec":
        form = data.get("form")
        return f"{form or 'SEC'} filing"
    return ev.source or "evidence"


def _evidence_published_at(ev: Evidence) -> datetime | None:
    data = ev.data or {}
    for key in ("published_at", "filing_date", "report_date"):
        raw = data.get(key)
        if not raw:
            continue
        if isinstance(raw, datetime):
            dt = raw
        else:
            try:
                dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            except ValueError:
                # date-only
                try:
                    dt = datetime.fromisoformat(str(raw)[:10]).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    if ev.timestamp.tzinfo is None:
        return ev.timestamp.replace(tzinfo=timezone.utc)
    return ev.timestamp


def in_window(
    published_at: datetime | None,
    *,
    now: datetime,
    window_hours: int,
) -> bool:
    if published_at is None:
        # Fail open for undated items so cache-only SEC metadata can still surface.
        return True
    return published_at >= now - timedelta(hours=window_hours)


def classify_evidence(
    items: Iterable[Evidence],
    *,
    now: datetime | None = None,
    window_hours: int = 24,
) -> list[ClassifiedEvent]:
    """Classify news/SEC evidence in the rolling window; skip uncategorized noise."""
    clock = now or datetime.now(timezone.utc)
    if clock.tzinfo is None:
        clock = clock.replace(tzinfo=timezone.utc)

    out: list[ClassifiedEvent] = []
    for ev in items:
        if ev.type not in ("news", "sec"):
            continue
        published = _evidence_published_at(ev)
        if not in_window(published, now=clock, window_hours=window_hours):
            continue
        title = _evidence_title(ev)
        category: BriefEventCategory | None = None
        if ev.type == "news":
            category = classify_headline(title)
        else:
            form = (ev.data or {}).get("form")
            form_s = str(form) if form is not None else None
            category = classify_sec_form(form_s) or classify_headline(title)
        if category is None:
            continue
        severity = CATEGORY_SEVERITY[category]
        url = ev.citation or (ev.data or {}).get("url")
        source_url = str(url) if url else None
        out.append(
            ClassifiedEvent(
                category=category,
                severity=severity,
                evidence=ev,
                title=title,
                source_url=source_url,
                published_at=published,
            )
        )
    # Severity then recency (newest first).
    out.sort(
        key=lambda e: (
            -e.severity,
            -(e.published_at.timestamp() if e.published_at else 0.0),
        )
    )
    return out

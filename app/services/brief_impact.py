"""Impact score, priority, and sentiment mapping for Brief triage."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from app.schemas.brief import (
    BriefEventCategory,
    BriefPriority,
    BriefSentiment,
    BriefSource,
)

# Base impact by category (plan scoring table).
CATEGORY_IMPACT_BASE: dict[BriefEventCategory, int] = {
    BriefEventCategory.SECURITY_BREACH: 96,
    BriefEventCategory.EARNINGS_GUIDANCE: 95,
    BriefEventCategory.REGULATORY_MATERIAL: 90,
    BriefEventCategory.ANALYST_RATING: 84,
    BriefEventCategory.PRODUCT_ANNOUNCEMENT: 79,
    BriefEventCategory.CONTRACTS_WON_LOST: 72,
    BriefEventCategory.OTHER_MATERIAL: 45,
    BriefEventCategory.PRICE_MOVE: 55,
}

# move_score 0–5 → impact when the signal is primarily a price move.
MOVE_SCORE_IMPACT: dict[int, int] = {
    0: 0,
    1: 30,
    2: 55,
    3: 75,
    4: 88,
    5: 95,
}

HIGH_PRIORITY_THRESHOLD = 80
MEDIUM_PRIORITY_THRESHOLD = 50

_THEME_LABELS: dict[BriefEventCategory, str] = {
    BriefEventCategory.EARNINGS_GUIDANCE: "Earnings",
    BriefEventCategory.SECURITY_BREACH: "Security",
    BriefEventCategory.CONTRACTS_WON_LOST: "Contracts",
    BriefEventCategory.REGULATORY_MATERIAL: "Regulatory",
    BriefEventCategory.ANALYST_RATING: "Analyst",
    BriefEventCategory.PRODUCT_ANNOUNCEMENT: "Products",
    BriefEventCategory.OTHER_MATERIAL: "Press",
    BriefEventCategory.PRICE_MOVE: "Price move",
}

_NEGATIVE_HINTS = (
    "miss",
    "cuts",
    "cut",
    "downgrade",
    "lawsuit",
    "sued",
    "breach",
    "investigation",
    "warning",
    "loss",
    "loses",
    "lost",
    "fraud",
    "probe",
    "halt",
    "recall",
    "resign",
    "fired",
    "decline",
    "falls",
    "plunges",
    "slump",
)

_POSITIVE_HINTS = (
    "beat",
    "beats",
    "upgrade",
    "raises",
    "raised",
    "win",
    "wins",
    "won",
    "approval",
    "approved",
    "award",
    "awarded",
    "launch",
    "partnership",
    "record",
    "surge",
    "soars",
    "jumps",
    "growth",
)


def impact_from_category(
    category: BriefEventCategory,
    *,
    severity: int | None = None,
    move_score: int | None = None,
    daily_return: float | None = None,
) -> int:
    """Map category (+ optional move) to impact 0–100."""
    if category == BriefEventCategory.PRICE_MOVE:
        if move_score is not None:
            return MOVE_SCORE_IMPACT.get(int(move_score), 55)
        if daily_return is not None:
            from app.services.yahoo_history import move_score as ms

            return MOVE_SCORE_IMPACT.get(ms(daily_return), 55)
        return CATEGORY_IMPACT_BASE[category]

    base = CATEGORY_IMPACT_BASE.get(category, 45)
    # Mild severity nudge (±3) without leaving category band.
    if severity is not None and severity >= 1:
        nudge = (int(severity) - 3) * 2
        base = max(20, min(100, base + nudge))
    # Large moves amplify event impact slightly.
    if move_score is not None and move_score >= 4:
        base = min(100, base + 3)
    return int(base)


def priority_from_impact(impact: int) -> BriefPriority | None:
    """High ≥80, Medium ≥50; below threshold → not surfaced as priority."""
    if impact >= HIGH_PRIORITY_THRESHOLD:
        return BriefPriority.HIGH
    if impact >= MEDIUM_PRIORITY_THRESHOLD:
        return BriefPriority.MEDIUM
    return None


def sentiment_from_text(
    text: str,
    *,
    daily_return: float | None = None,
    category: BriefEventCategory | None = None,
) -> BriefSentiment:
    """Heuristic sentiment from headline + optional daily return."""
    lower = (text or "").lower()
    neg = sum(1 for h in _NEGATIVE_HINTS if h in lower)
    pos = sum(1 for h in _POSITIVE_HINTS if h in lower)
    if category == BriefEventCategory.SECURITY_BREACH:
        neg += 2
    if pos > neg:
        return BriefSentiment.POSITIVE
    if neg > pos:
        return BriefSentiment.NEGATIVE
    if daily_return is not None:
        if daily_return <= -0.05:
            return BriefSentiment.NEGATIVE
        if daily_return >= 0.05:
            return BriefSentiment.POSITIVE
    return BriefSentiment.NEUTRAL


def theme_label(category: BriefEventCategory) -> str:
    return _THEME_LABELS.get(category, "Other")


def source_label_from_url(url: str | None, fallback: str = "Source") -> str:
    if not url:
        return fallback
    try:
        host = urlparse(url).netloc.lower()
    except Exception:  # noqa: BLE001
        return fallback
    host = host.removeprefix("www.")
    if not host:
        return fallback
    # Short brand-ish label.
    brand = host.split(".")[0]
    known = {
        "reuters": "Reuters",
        "bloomberg": "Bloomberg",
        "seekingalpha": "Seeking Alpha",
        "sec": "SEC",
        "edgar": "SEC Filing",
        "yahoo": "Yahoo Finance",
        "cnbc": "CNBC",
        "wsj": "WSJ",
        "ft": "FT",
        "marketwatch": "MarketWatch",
        "businesswire": "Business Wire",
        "prnewswire": "PR Newswire",
        "google": "Google News",
    }
    for key, label in known.items():
        if key in host:
            return label
    return brand.capitalize() if brand else fallback


def sources_for_bullet(
    *,
    source_url: str | None,
    category: BriefEventCategory,
    evidence_ids: list[str] | None = None,
) -> list[BriefSource]:
    sources: list[BriefSource] = []
    if source_url:
        sources.append(
            BriefSource(
                label=source_label_from_url(source_url),
                url=source_url,
            )
        )
    if category == BriefEventCategory.REGULATORY_MATERIAL and not any(
        s.label.startswith("SEC") for s in sources
    ):
        sources.append(BriefSource(label="SEC Filing", url=source_url))
    if not sources and evidence_ids:
        sources.append(BriefSource(label="Evidence", url=None))
    return sources


def event_key(ticker: str, category: BriefEventCategory, text: str, evidence_id: str | None) -> str:
    """Stable-ish key for unread tracking."""
    if evidence_id:
        return f"{ticker}:{evidence_id}"
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower())[:40].strip("-")
    return f"{ticker}:{category.value}:{slug}"


def portfolio_impact_line(
    *,
    list_kind: str,
    held_count: int,
) -> str:
    if list_kind == "held":
        if held_count <= 0:
            return "Held position — review if material to your thesis."
        pct = 100.0 / held_count
        return f"Held · equal-weight ~{pct:.1f}% of Held book ({held_count} names)."
    return "Watched — not in Held book; relevant for promote / add decisions."


def category_headline(category: BriefEventCategory) -> str:
    return {
        BriefEventCategory.EARNINGS_GUIDANCE: "Earnings / Guidance",
        BriefEventCategory.SECURITY_BREACH: "Security Incident",
        BriefEventCategory.CONTRACTS_WON_LOST: "Contract Activity",
        BriefEventCategory.REGULATORY_MATERIAL: "Regulatory / Legal",
        BriefEventCategory.ANALYST_RATING: "Analyst Rating",
        BriefEventCategory.PRODUCT_ANNOUNCEMENT: "Product Announcement",
        BriefEventCategory.OTHER_MATERIAL: "Material Press",
        BriefEventCategory.PRICE_MOVE: "Large Price Move",
    }.get(category, "Material Event")

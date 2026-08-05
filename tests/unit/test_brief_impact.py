"""Impact score / priority / sentiment mapping."""

from __future__ import annotations

from app.schemas.brief import BriefEventCategory, BriefPriority, BriefSentiment
from app.services.brief_impact import (
    impact_from_category,
    portfolio_impact_line,
    priority_from_impact,
    sentiment_from_text,
    theme_label,
)


def test_category_impact_table() -> None:
    assert impact_from_category(BriefEventCategory.EARNINGS_GUIDANCE) >= 90
    assert impact_from_category(BriefEventCategory.ANALYST_RATING) == 84
    assert impact_from_category(BriefEventCategory.PRODUCT_ANNOUNCEMENT) == 79
    assert impact_from_category(BriefEventCategory.OTHER_MATERIAL) == 45


def test_price_move_from_move_score() -> None:
    assert impact_from_category(
        BriefEventCategory.PRICE_MOVE, move_score=5
    ) == 95
    assert impact_from_category(
        BriefEventCategory.PRICE_MOVE, move_score=2
    ) == 55


def test_priority_thresholds() -> None:
    assert priority_from_impact(95) == BriefPriority.HIGH
    assert priority_from_impact(80) == BriefPriority.HIGH
    assert priority_from_impact(79) == BriefPriority.MEDIUM
    assert priority_from_impact(50) == BriefPriority.MEDIUM
    assert priority_from_impact(49) is None


def test_sentiment_hints() -> None:
    assert (
        sentiment_from_text("Goldman upgrades NVDA on AI demand")
        == BriefSentiment.POSITIVE
    )
    assert (
        sentiment_from_text("Company misses earnings estimates")
        == BriefSentiment.NEGATIVE
    )
    assert (
        sentiment_from_text("Routine conference mention", daily_return=0.01)
        == BriefSentiment.NEUTRAL
    )


def test_portfolio_impact_equal_weight() -> None:
    assert "equal-weight" in portfolio_impact_line(list_kind="held", held_count=10)
    assert "Watched" in portfolio_impact_line(list_kind="watched", held_count=10)


def test_theme_label() -> None:
    assert theme_label(BriefEventCategory.ANALYST_RATING) == "Analyst"

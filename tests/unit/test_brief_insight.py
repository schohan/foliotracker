"""Brief insight provider modes."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from app.configs.settings import Settings
from app.schemas.brief import BriefEventCategory, BriefInsightMode, BriefSentiment
from app.services.brief_insight import build_insight, parse_insight_mode


def _settings(tmp_path: Path, mode: str = "deterministic") -> Settings:
    return Settings(
        watchlist_path=tmp_path / "w.json",
        source_cache_dir=tmp_path / "sources",
        phase0_cache_dir=tmp_path / "phase0",
        brief_store_path=tmp_path / "briefs.json",
        brief_miss_log_path=tmp_path / "misses.jsonl",
        brief_insight_mode=mode,
        google_api_key="fake-key",
    )


def test_parse_insight_mode() -> None:
    assert parse_insight_mode("deterministic") == BriefInsightMode.DETERMINISTIC
    assert parse_insight_mode("CANNED") == BriefInsightMode.CANNED
    assert parse_insight_mode("llm") == BriefInsightMode.LLM
    assert parse_insight_mode("nope") == BriefInsightMode.DETERMINISTIC


def test_deterministic_insight(tmp_path: Path) -> None:
    s = _settings(tmp_path, "deterministic")
    insight = build_insight(
        ticker="NVDA",
        category=BriefEventCategory.ANALYST_RATING,
        text="Goldman upgrades NVDA",
        list_kind="held",
        daily_return=0.04,
        sentiment=BriefSentiment.POSITIVE,
        impact=84,
        confidence=70,
        mode=BriefInsightMode.DETERMINISTIC,
        app_settings=s,
    )
    assert insight.provider == BriefInsightMode.DETERMINISTIC
    assert "Goldman" in insight.what_happened or "upgrade" in insight.what_happened.lower()
    assert insight.explain_busy
    assert "buy now" not in insight.suggested_action.lower()


def test_canned_insight(tmp_path: Path) -> None:
    s = _settings(tmp_path, "canned")
    insight = build_insight(
        ticker="LITE",
        category=BriefEventCategory.EARNINGS_GUIDANCE,
        text="Revenue missed",
        list_kind="held",
        daily_return=-0.08,
        sentiment=BriefSentiment.NEGATIVE,
        impact=95,
        confidence=80,
        app_settings=s,
    )
    assert insight.provider == BriefInsightMode.CANNED
    assert insight.should_long_term_care in {"YES", "MAYBE", "NO"}
    assert len(insight.explain_busy) > 20


def test_llm_fail_closed_to_deterministic(tmp_path: Path) -> None:
    s = _settings(tmp_path, "llm")
    with patch("app.services.brief_insight.llm_insight", return_value=None):
        insight = build_insight(
            ticker="APH",
            category=BriefEventCategory.PRICE_MOVE,
            text="Session move +6%",
            list_kind="watched",
            daily_return=0.06,
            sentiment=BriefSentiment.POSITIVE,
            impact=75,
            confidence=40,
            mode=BriefInsightMode.LLM,
            app_settings=s,
        )
    assert insight.provider == BriefInsightMode.DETERMINISTIC


def test_llm_success(tmp_path: Path) -> None:
    s = _settings(tmp_path, "llm")
    fake = MagicMock()
    fake.models.generate_content.return_value = MagicMock(
        text=(
            '{"what_happened":"Upgrade","why":"AI demand",'
            '"market_reaction":"+4%","should_long_term_care":"YES",'
            '"confidence_label":"High","suggested_action":"Read report",'
            '"explain_busy":"Analyst raised target on stronger demand."}'
        )
    )
    with patch("google.genai.Client", return_value=fake):
        insight = build_insight(
            ticker="NVDA",
            category=BriefEventCategory.ANALYST_RATING,
            text="Upgrade",
            list_kind="held",
            daily_return=0.04,
            sentiment=BriefSentiment.POSITIVE,
            impact=84,
            confidence=70,
            mode=BriefInsightMode.LLM,
            app_settings=s,
        )
    assert insight.provider == BriefInsightMode.LLM
    assert insight.what_happened == "Upgrade"

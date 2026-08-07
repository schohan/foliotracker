"""Thesis change narrative — insight modes fail-closed."""

from __future__ import annotations

from datetime import datetime, timezone

from app.configs.settings import Settings
from app.schemas.thesis import ThesisChange, ThesisInsightMode, ThesisVerdict
from app.services.thesis_insight import (
    canned_narrative,
    deterministic_narrative,
    narrate_change,
    parse_insight_mode,
)


NOW = datetime(2026, 8, 7, tzinfo=timezone.utc)


def _change(
    verdict: ThesisVerdict = ThesisVerdict.NO_CHANGE,
    evidence: list[str] | None = None,
) -> ThesisChange:
    return ThesisChange(
        verdict=verdict,
        as_of=NOW,
        evidence=evidence or ["baseline — no prior quarter"],
    )


def test_parse_insight_mode() -> None:
    assert parse_insight_mode("canned") == ThesisInsightMode.CANNED
    assert parse_insight_mode("bogus") == ThesisInsightMode.DETERMINISTIC


def test_deterministic_narrative() -> None:
    text = deterministic_narrative(_change(ThesisVerdict.BROKEN, ["mos +0.1 → -0.05"]))
    assert "Broken" in text
    assert "mos" in text


def test_canned_narrative() -> None:
    text = canned_narrative(_change(ThesisVerdict.STRENGTHENED, ["fs_score 60 → 75"]))
    assert "stronger" in text.lower()
    assert "fs_score" in text


def test_narrate_deterministic_default() -> None:
    s = Settings(thesis_insight_mode="deterministic")
    out = narrate_change(_change(), app_settings=s)
    assert out.insight_mode == "deterministic"
    assert out.narrative


def test_narrate_canned() -> None:
    s = Settings(thesis_insight_mode="canned")
    out = narrate_change(
        _change(ThesisVerdict.SLIGHTLY_WEAKER, ["graham_score 70 → 55"]),
        app_settings=s,
    )
    assert out.insight_mode == "canned"
    assert "weaker" in out.narrative.lower()


def test_llm_fail_closed_without_key() -> None:
    s = Settings(thesis_insight_mode="llm", google_api_key=None)
    out = narrate_change(_change(), ticker="NVDA", app_settings=s)
    assert out.insight_mode == "deterministic"
    assert out.narrative

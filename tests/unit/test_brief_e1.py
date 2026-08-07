"""Brief E1 — affected frameworks + morning counts."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

from app.schemas.brief import BriefEventCategory, BriefOpportunityScore
from app.schemas.thesis import (
    ThesisChange,
    ThesisDashboard,
    ThesisGenerationStatus,
    ThesisMonitoring,
    ThesisSignalVector,
    ThesisSnapshot,
    ThesisTicker,
    ThesisVerdict,
)
from app.services.brief_e1 import (
    affected_frameworks_for,
    build_morning_counts,
    thesis_impact_line,
)


def test_affected_frameworks_map() -> None:
    assert affected_frameworks_for(BriefEventCategory.EARNINGS_GUIDANCE) == [
        "graham",
        "financial_strength",
    ]
    assert affected_frameworks_for(BriefEventCategory.PRICE_MOVE) == ["graham"]
    assert affected_frameworks_for(BriefEventCategory.OTHER_MATERIAL) == []


def test_thesis_impact_line_from_monitoring() -> None:
    row = ThesisTicker(
        ticker="AAA",
        list_kind="held",
        monitoring=ThesisMonitoring(
            original_thesis="baseline",
            current=ThesisChange(
                verdict=ThesisVerdict.STRENGTHENED,
                as_of=datetime.now(timezone.utc),
                evidence=["graham_score 40 → 55 (+15)"],
            ),
        ),
    )
    assert thesis_impact_line(row) == "Strengthened: graham_score 40 → 55 (+15)"
    assert thesis_impact_line(None) is None
    assert thesis_impact_line(ThesisTicker(ticker="B", list_kind="watched")) is None


def test_morning_counts_without_thesis() -> None:
    counts = build_morning_counts(None)
    assert counts.thesis_available is False
    assert counts.opportunity_score is None
    assert counts.thesis_changed == 0


def _dash(*rows: ThesisTicker) -> ThesisDashboard:
    return ThesisDashboard(
        generated_at=datetime.now(timezone.utc),
        generation_status=ThesisGenerationStatus.COMPLETE,
        universe_count=len(rows),
        tickers_considered=len(rows),
        tickers=list(rows),
    )


def _row(
    ticker: str,
    verdict: ThesisVerdict,
) -> ThesisTicker:
    return ThesisTicker(
        ticker=ticker,
        list_kind="held",
        monitoring=ThesisMonitoring(
            original_thesis="x",
            current=ThesisChange(
                verdict=verdict,
                as_of=datetime.now(timezone.utc),
                evidence=["signal"],
            ),
        ),
    )


def test_morning_counts_verdicts_and_opportunity() -> None:
    dash = _dash(
        _row("A", ThesisVerdict.STRENGTHENED),
        _row("B", ThesisVerdict.STRENGTHENED),
        _row("C", ThesisVerdict.BROKEN),
        _row("D", ThesisVerdict.NO_CHANGE),
    )

    def fake_snaps(ticker: str, *, app_settings=None):
        # A: graham + mos up; B: mos up; C: fs drop; D: flat
        if ticker == "A":
            return [
                ThesisSnapshot(
                    ticker="A",
                    as_of=datetime.now(timezone.utc),
                    original_thesis="o",
                    signals=ThesisSignalVector(
                        graham_score=60, fs_score=50, mos=0.25
                    ),
                    change=ThesisChange(
                        verdict=ThesisVerdict.STRENGTHENED,
                        as_of=datetime.now(timezone.utc),
                    ),
                ),
                ThesisSnapshot(
                    ticker="A",
                    as_of=datetime.now(timezone.utc),
                    original_thesis="o",
                    signals=ThesisSignalVector(
                        graham_score=40, fs_score=50, mos=0.10
                    ),
                    change=ThesisChange(
                        verdict=ThesisVerdict.NO_CHANGE,
                        as_of=datetime.now(timezone.utc),
                    ),
                ),
            ]
        if ticker == "B":
            return [
                ThesisSnapshot(
                    ticker="B",
                    as_of=datetime.now(timezone.utc),
                    original_thesis="o",
                    signals=ThesisSignalVector(graham_score=50, mos=0.30),
                    change=ThesisChange(
                        verdict=ThesisVerdict.STRENGTHENED,
                        as_of=datetime.now(timezone.utc),
                    ),
                ),
                ThesisSnapshot(
                    ticker="B",
                    as_of=datetime.now(timezone.utc),
                    original_thesis="o",
                    signals=ThesisSignalVector(graham_score=50, mos=0.15),
                    change=ThesisChange(
                        verdict=ThesisVerdict.NO_CHANGE,
                        as_of=datetime.now(timezone.utc),
                    ),
                ),
            ]
        if ticker == "C":
            return [
                ThesisSnapshot(
                    ticker="C",
                    as_of=datetime.now(timezone.utc),
                    original_thesis="o",
                    signals=ThesisSignalVector(fs_score=30, mos=0.05),
                    change=ThesisChange(
                        verdict=ThesisVerdict.BROKEN,
                        as_of=datetime.now(timezone.utc),
                    ),
                ),
                ThesisSnapshot(
                    ticker="C",
                    as_of=datetime.now(timezone.utc),
                    original_thesis="o",
                    signals=ThesisSignalVector(fs_score=50, mos=0.05),
                    change=ThesisChange(
                        verdict=ThesisVerdict.NO_CHANGE,
                        as_of=datetime.now(timezone.utc),
                    ),
                ),
            ]
        return [
            ThesisSnapshot(
                ticker="D",
                as_of=datetime.now(timezone.utc),
                original_thesis="o",
                signals=ThesisSignalVector(graham_score=50, mos=0.1),
                change=ThesisChange(
                    verdict=ThesisVerdict.NO_CHANGE,
                    as_of=datetime.now(timezone.utc),
                ),
            )
        ]

    with patch("app.services.brief_e1.thesis_store.get_snapshots", side_effect=fake_snaps):
        counts = build_morning_counts(dash)

    assert counts.thesis_available is True
    assert counts.thesis_changed == 3  # A,B strengthened + C broken
    assert counts.valuation_improved == 1  # A graham +20
    assert counts.mos_increased == 2  # A +0.15, B +0.15
    assert counts.balance_sheet_weakened == 1  # C fs -20
    assert counts.risk_increased == 1  # C broken
    # opp = 1 + 2 + 2 strengthened = 5; risk = 1 + 1 = 2 → high
    assert counts.opportunity_score == BriefOpportunityScore.HIGH


def test_morning_counts_low_when_risk_dominates() -> None:
    dash = _dash(
        _row("X", ThesisVerdict.BROKEN),
        _row("Y", ThesisVerdict.SLIGHTLY_WEAKER),
    )

    def fake_snaps(ticker: str, *, app_settings=None):
        return [
            ThesisSnapshot(
                ticker=ticker,
                as_of=datetime.now(timezone.utc),
                original_thesis="o",
                signals=ThesisSignalVector(fs_score=20),
                change=ThesisChange(
                    verdict=ThesisVerdict.BROKEN,
                    as_of=datetime.now(timezone.utc),
                ),
            ),
            ThesisSnapshot(
                ticker=ticker,
                as_of=datetime.now(timezone.utc),
                original_thesis="o",
                signals=ThesisSignalVector(fs_score=45),
                change=ThesisChange(
                    verdict=ThesisVerdict.NO_CHANGE,
                    as_of=datetime.now(timezone.utc),
                ),
            ),
        ]

    with patch("app.services.brief_e1.thesis_store.get_snapshots", side_effect=fake_snaps):
        counts = build_morning_counts(dash)

    assert counts.risk_increased == 2
    assert counts.balance_sheet_weakened == 2
    assert counts.opportunity_score == BriefOpportunityScore.LOW

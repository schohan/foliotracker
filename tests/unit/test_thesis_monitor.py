"""Thesis Monitoring T3 — locked quarterly verdict rules."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.schemas.thesis import ThesisSignalVector, ThesisVerdict
from app.services.thesis_monitor import (
    assess_change,
    should_append_snapshot,
    synthesize_original_thesis,
)


NOW = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)


def _sig(**overrides) -> ThesisSignalVector:
    base = dict(
        graham_score=70.0,
        fs_score=80.0,
        mos=0.20,
        net_cash_ok=True,
        current_ratio=2.0,
        fcf_positive=True,
    )
    base.update(overrides)
    return ThesisSignalVector(**base)


def test_baseline_no_prior() -> None:
    change = assess_change(None, _sig(), as_of=NOW)
    assert change.verdict == ThesisVerdict.NO_CHANGE
    assert change.evidence == ["baseline — no prior quarter"]


def test_broken_graham_drop() -> None:
    prior = _sig(graham_score=70.0)
    current = _sig(graham_score=40.0)  # −30 ≥ 25
    change = assess_change(prior, current, as_of=NOW)
    assert change.verdict == ThesisVerdict.BROKEN
    assert any("graham_score" in e for e in change.evidence)


def test_broken_mos_cross() -> None:
    prior = _sig(mos=0.12)
    current = _sig(mos=-0.05)
    change = assess_change(prior, current, as_of=NOW)
    assert change.verdict == ThesisVerdict.BROKEN


def test_broken_net_cash_flip() -> None:
    prior = _sig(net_cash_ok=True)
    current = _sig(net_cash_ok=False)
    change = assess_change(prior, current, as_of=NOW)
    assert change.verdict == ThesisVerdict.BROKEN


def test_slightly_weaker_score_drop() -> None:
    prior = _sig(graham_score=70.0)
    current = _sig(graham_score=55.0)  # −15
    change = assess_change(prior, current, as_of=NOW)
    assert change.verdict == ThesisVerdict.SLIGHTLY_WEAKER


def test_slightly_weaker_mos_drop() -> None:
    prior = _sig(mos=0.25)
    current = _sig(mos=0.10)  # −0.15
    change = assess_change(prior, current, as_of=NOW)
    assert change.verdict == ThesisVerdict.SLIGHTLY_WEAKER


def test_strengthened_score_rise() -> None:
    prior = _sig(fs_score=60.0)
    current = _sig(fs_score=75.0)
    change = assess_change(prior, current, as_of=NOW)
    assert change.verdict == ThesisVerdict.STRENGTHENED


def test_no_change_small_delta() -> None:
    prior = _sig(graham_score=70.0, mos=0.20)
    current = _sig(graham_score=72.0, mos=0.22)
    change = assess_change(prior, current, as_of=NOW)
    assert change.verdict == ThesisVerdict.NO_CHANGE


def test_null_scores_skipped() -> None:
    prior = _sig(graham_score=None, fs_score=80.0)
    current = _sig(graham_score=10.0, fs_score=80.0)
    change = assess_change(prior, current, as_of=NOW)
    # Graham skipped (prior null); FS unchanged → no change
    assert change.verdict == ThesisVerdict.NO_CHANGE
    assert not any("graham_score" in e for e in change.evidence)


def test_broken_beats_strengthened() -> None:
    # Graham broken drop + MoS rise — Broken wins
    prior = _sig(graham_score=80.0, mos=0.10)
    current = _sig(graham_score=50.0, mos=0.30)
    change = assess_change(prior, current, as_of=NOW)
    assert change.verdict == ThesisVerdict.BROKEN


def test_quarter_gate() -> None:
    assert should_append_snapshot(None, now=NOW, quarter_days=90, force_refresh=False)
    assert should_append_snapshot(NOW, now=NOW, quarter_days=90, force_refresh=True)
    assert not should_append_snapshot(
        NOW - timedelta(days=30), now=NOW, quarter_days=90, force_refresh=False
    )
    assert should_append_snapshot(
        NOW - timedelta(days=91), now=NOW, quarter_days=90, force_refresh=False
    )


def test_synthesize_original_thesis() -> None:
    text = synthesize_original_thesis(
        graham_score=91.0, fs_score=80.0, mos=0.34
    )
    assert "Graham 91" in text
    assert "MoS 34%" in text

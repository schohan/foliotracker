"""Thesis Monitoring T3 — deterministic quarterly change assessment.

Implements the locked verdict table in architecture.md "Thesis monitoring
specs" (2026-08-07). Pure Python; missing signals skipped, never invented.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.schemas.financials import FinancialMetrics
from app.schemas.thesis import (
    FrameworkId,
    FrameworkScorecard,
    MarginOfSafetyView,
    ThesisChange,
    ThesisSignalVector,
    ThesisVerdict,
)

# Locked thresholds
_GRAHAM_BROKEN = 25.0
_FS_BROKEN = 30.0
_SCORE_WEAKER = 10.0
_SCORE_STRONGER = 10.0
_MOS_WEAKER = 0.10
_MOS_STRONGER = 0.10


def signals_from(
    *,
    frameworks: list[FrameworkScorecard],
    mos_view: MarginOfSafetyView | None,
    metrics: FinancialMetrics,
) -> ThesisSignalVector:
    """Build comparable signal vector from T1–T2 outputs + fundamentals."""
    graham: float | None = None
    fs: float | None = None
    for card in frameworks:
        if card.framework == FrameworkId.GRAHAM:
            graham = card.score
        elif card.framework == FrameworkId.FINANCIAL_STRENGTH:
            fs = card.score

    net_cash_ok: bool | None = None
    if metrics.total_cash is not None and metrics.total_debt is not None:
        net_cash_ok = metrics.total_cash >= metrics.total_debt

    fcf = metrics.free_cash_flow
    if fcf is None and metrics.cash_flow is not None:
        fcf = metrics.cash_flow.free_cash_flow
    fcf_positive: bool | None = None if fcf is None else fcf > 0

    return ThesisSignalVector(
        graham_score=graham,
        fs_score=fs,
        mos=mos_view.margin_of_safety if mos_view is not None else None,
        net_cash_ok=net_cash_ok,
        current_ratio=metrics.current_ratio,
        fcf_positive=fcf_positive,
    )


def _fmt_num(v: float) -> str:
    if abs(v) >= 100 or abs(v - round(v)) < 1e-9:
        return f"{v:.0f}"
    return f"{v:.2f}"


def _score_delta_line(name: str, prior: float, current: float) -> str:
    delta = current - prior
    sign = "+" if delta > 0 else ""
    return f"{name} {_fmt_num(prior)} → {_fmt_num(current)} ({sign}{_fmt_num(delta)})"


def assess_change(
    prior: ThesisSignalVector | None,
    current: ThesisSignalVector,
    *,
    as_of: datetime | None = None,
) -> ThesisChange:
    """Compare current vs prior → closed verdict + evidence (no narrative)."""
    clock = as_of or datetime.now(timezone.utc)
    if clock.tzinfo is None:
        clock = clock.replace(tzinfo=timezone.utc)

    if prior is None:
        return ThesisChange(
            verdict=ThesisVerdict.NO_CHANGE,
            as_of=clock,
            evidence=["baseline — no prior quarter"],
        )

    evidence: list[str] = []
    broken = False
    weaker = False
    stronger = False

    # Graham score
    if prior.graham_score is not None and current.graham_score is not None:
        drop = prior.graham_score - current.graham_score
        rise = current.graham_score - prior.graham_score
        if abs(drop) >= 0.5 or abs(rise) >= 0.5:
            evidence.append(
                _score_delta_line("graham_score", prior.graham_score, current.graham_score)
            )
        if drop >= _GRAHAM_BROKEN:
            broken = True
        elif drop >= _SCORE_WEAKER:
            weaker = True
        elif rise >= _SCORE_STRONGER:
            stronger = True

    # FS score
    if prior.fs_score is not None and current.fs_score is not None:
        drop = prior.fs_score - current.fs_score
        rise = current.fs_score - prior.fs_score
        if abs(drop) >= 0.5 or abs(rise) >= 0.5:
            evidence.append(
                _score_delta_line("fs_score", prior.fs_score, current.fs_score)
            )
        if drop >= _FS_BROKEN:
            broken = True
        elif drop >= _SCORE_WEAKER:
            weaker = True
        elif rise >= _SCORE_STRONGER:
            stronger = True

    # MoS
    if prior.mos is not None and current.mos is not None:
        delta = current.mos - prior.mos
        if abs(delta) >= 0.005 or (prior.mos >= 0) != (current.mos >= 0):
            evidence.append(
                f"mos {prior.mos:+.2f} → {current.mos:+.2f}"
            )
        if prior.mos >= 0 and current.mos < 0:
            broken = True
        elif (-delta) >= _MOS_WEAKER:
            weaker = True
        elif delta >= _MOS_STRONGER:
            stronger = True

    # Net cash flip true → false
    if prior.net_cash_ok is True and current.net_cash_ok is False:
        evidence.append("net_cash_ok true → false")
        broken = True
    elif (
        prior.net_cash_ok is not None
        and current.net_cash_ok is not None
        and prior.net_cash_ok != current.net_cash_ok
    ):
        evidence.append(
            f"net_cash_ok {str(prior.net_cash_ok).lower()} → {str(current.net_cash_ok).lower()}"
        )

    if broken:
        verdict = ThesisVerdict.BROKEN
    elif weaker:
        verdict = ThesisVerdict.SLIGHTLY_WEAKER
    elif stronger:
        verdict = ThesisVerdict.STRENGTHENED
    else:
        verdict = ThesisVerdict.NO_CHANGE
        if not evidence:
            evidence = ["no material signal deltas vs prior quarter"]

    return ThesisChange(
        verdict=verdict,
        as_of=clock,
        evidence=evidence,
    )


def should_append_snapshot(
    prior_as_of: datetime | None,
    *,
    now: datetime,
    quarter_days: int,
    force_refresh: bool,
) -> bool:
    """Quarter gate: append on first / aged / force_refresh."""
    if force_refresh or prior_as_of is None:
        return True
    prior = prior_as_of
    if prior.tzinfo is None:
        prior = prior.replace(tzinfo=timezone.utc)
    clock = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
    age_days = (clock - prior).total_seconds() / 86400.0
    return age_days >= float(quarter_days)


def synthesize_original_thesis(
    *,
    graham_score: float | None,
    fs_score: float | None,
    mos: float | None,
) -> str:
    """Deterministic fallback when Phase0 thesis and prior snapshot are absent."""
    parts: list[str] = []
    if graham_score is not None:
        parts.append(f"Graham {graham_score:.0f}")
    else:
        parts.append("Graham —")
    if fs_score is not None:
        parts.append(f"Financial Strength {fs_score:.0f}")
    else:
        parts.append("Financial Strength —")
    if mos is not None:
        parts.append(f"MoS {mos * 100:.0f}%")
    else:
        parts.append("MoS —")
    return "; ".join(parts) + "."

"""Brief E1 — bullet thesis linkage + morning portfolio counts.

Implements architecture.md "Brief E1 enrichment specs" (2026-08-07).
Read-only over Thesis store; never regenerates Thesis or Phase0.
"""

from __future__ import annotations

from app.configs.settings import Settings
from app.schemas.brief import (
    BriefEventCategory,
    BriefMorningCounts,
    BriefOpportunityScore,
)
from app.schemas.thesis import (
    FrameworkId,
    THESIS_VERDICT_LABELS,
    ThesisDashboard,
    ThesisSignalVector,
    ThesisTicker,
    ThesisVerdict,
)
from app.services import thesis_store

# Locked thresholds (match thesis_monitor score/MoS stronger-weaker bands).
_SCORE_DELTA = 10.0
_MOS_DELTA = 0.10

_CHANGED = {
    ThesisVerdict.STRENGTHENED,
    ThesisVerdict.SLIGHTLY_WEAKER,
    ThesisVerdict.BROKEN,
}
_RISK = {ThesisVerdict.SLIGHTLY_WEAKER, ThesisVerdict.BROKEN}

# Category → frameworks (architecture E1 map).
_CATEGORY_FRAMEWORKS: dict[BriefEventCategory, list[str]] = {
    BriefEventCategory.EARNINGS_GUIDANCE: [
        FrameworkId.GRAHAM.value,
        FrameworkId.FINANCIAL_STRENGTH.value,
    ],
    BriefEventCategory.SECURITY_BREACH: [FrameworkId.FINANCIAL_STRENGTH.value],
    BriefEventCategory.CONTRACTS_WON_LOST: [FrameworkId.GRAHAM.value],
    BriefEventCategory.REGULATORY_MATERIAL: [FrameworkId.FINANCIAL_STRENGTH.value],
    BriefEventCategory.ANALYST_RATING: [
        FrameworkId.GRAHAM.value,
        FrameworkId.FINANCIAL_STRENGTH.value,
    ],
    BriefEventCategory.PRODUCT_ANNOUNCEMENT: [FrameworkId.GRAHAM.value],
    BriefEventCategory.PRICE_MOVE: [FrameworkId.GRAHAM.value],
    BriefEventCategory.OTHER_MATERIAL: [],
}


def affected_frameworks_for(category: BriefEventCategory) -> list[str]:
    """Deterministic category → FrameworkId values."""
    return list(_CATEGORY_FRAMEWORKS.get(category, []))


def thesis_impact_line(row: ThesisTicker | None) -> str | None:
    """Short thesis-impact line from monitoring current change, or null."""
    if row is None or row.monitoring is None:
        return None
    current = row.monitoring.current
    if current is None:
        return None
    label = THESIS_VERDICT_LABELS.get(current.verdict, current.verdict.value)
    detail = ""
    if current.evidence:
        detail = current.evidence[0]
    elif current.narrative:
        detail = current.narrative.strip()
    if detail:
        return f"{label}: {detail}"[:220]
    return label


def _prior_current_signals(
    ticker: str,
    *,
    app_settings: Settings | None = None,
) -> tuple[ThesisSignalVector | None, ThesisSignalVector | None]:
    """Newest snapshot = current; second = prior. Missing → (None, None) parts."""
    snaps = thesis_store.get_snapshots(ticker, app_settings=app_settings)
    if not snaps:
        return None, None
    current = snaps[0].signals
    prior = snaps[1].signals if len(snaps) >= 2 else None
    return prior, current


def build_morning_counts(
    dashboard: ThesisDashboard | None,
    *,
    app_settings: Settings | None = None,
) -> BriefMorningCounts:
    """Portfolio morning strip from latest Thesis dashboard + snapshot rings."""
    if dashboard is None or not dashboard.tickers:
        return BriefMorningCounts(thesis_available=False)

    thesis_changed = 0
    valuation_improved = 0
    mos_increased = 0
    balance_sheet_weakened = 0
    risk_increased = 0
    strengthened = 0

    for row in dashboard.tickers:
        verdict: ThesisVerdict | None = None
        if row.monitoring and row.monitoring.current:
            verdict = row.monitoring.current.verdict

        if verdict in _CHANGED:
            thesis_changed += 1
        if verdict in _RISK:
            risk_increased += 1
        if verdict == ThesisVerdict.STRENGTHENED:
            strengthened += 1

        prior, current = _prior_current_signals(
            row.ticker, app_settings=app_settings
        )
        if prior is None or current is None:
            continue

        if (
            prior.graham_score is not None
            and current.graham_score is not None
            and (current.graham_score - prior.graham_score) >= _SCORE_DELTA
        ):
            valuation_improved += 1

        if (
            prior.mos is not None
            and current.mos is not None
            and (current.mos - prior.mos) >= _MOS_DELTA
        ):
            mos_increased += 1

        if (
            prior.fs_score is not None
            and current.fs_score is not None
            and (prior.fs_score - current.fs_score) >= _SCORE_DELTA
        ):
            balance_sheet_weakened += 1

    opp = valuation_improved + mos_increased + strengthened
    risk = balance_sheet_weakened + risk_increased
    if opp >= 3 and opp > risk:
        opportunity: BriefOpportunityScore | None = BriefOpportunityScore.HIGH
    elif risk > opp and risk >= 1:
        opportunity = BriefOpportunityScore.LOW
    else:
        opportunity = BriefOpportunityScore.MEDIUM

    return BriefMorningCounts(
        thesis_changed=thesis_changed,
        valuation_improved=valuation_improved,
        mos_increased=mos_increased,
        balance_sheet_weakened=balance_sheet_weakened,
        risk_increased=risk_increased,
        opportunity_score=opportunity,
        thesis_available=True,
    )

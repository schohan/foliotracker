"""AI Portfolio Advisor + research explain (T4)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from app.configs.settings import Settings
from app.schemas.financials import FinancialMetrics, StatementSummary
from app.schemas.thesis import (
    AdvisorConclusion,
    AssetBreakdown,
    AssetVerdict,
    FrameworkId,
    FrameworkScorecard,
    MarginOfSafetyView,
    ThesisChange,
    ThesisInsightMode,
    ThesisMonitoring,
    ThesisTicker,
    ThesisVerdict,
)
from app.services.thesis_advisor import (
    build_advisor,
    explain_for_row,
    resolve_question,
    select_conclusion,
)
from app.services.thesis_frameworks import scorecards_for


def _card(framework: FrameworkId, score: float | None) -> FrameworkScorecard:
    return FrameworkScorecard(
        framework=framework,
        label=framework.value,
        score=score,
        coverage=80 if score is not None else 0,
    )


def _monitoring(verdict: ThesisVerdict) -> ThesisMonitoring:
    return ThesisMonitoring(
        original_thesis="seed",
        current=ThesisChange(
            verdict=verdict,
            as_of=datetime(2026, 8, 7, tzinfo=timezone.utc),
            evidence=["graham_score 70 → 40 (−30)"]
            if verdict == ThesisVerdict.BROKEN
            else ["baseline — no prior quarter"],
        ),
        timeline=[],
    )


def _mos(frac: float | None) -> MarginOfSafetyView | None:
    if frac is None:
        return None
    return MarginOfSafetyView(
        intrinsic_value=100.0,
        market_price=100.0 * (1 - frac) if frac < 1 else 50.0,
        margin_of_safety=frac,
        stars=4 if frac >= 0.3 else 2,
        rating="Excellent" if frac >= 0.3 else ("Poor" if frac < 0 else "Fair"),
    )


def test_resolve_question_canned() -> None:
    qid, text = resolve_question("most_bullish", "")
    assert qid == "most_bullish"
    assert "bullish" in text.lower()


def test_broken_thesis_research_further() -> None:
    conclusion = select_conclusion(
        frameworks=[
            _card(FrameworkId.GRAHAM, 70),
            _card(FrameworkId.FINANCIAL_STRENGTH, 70),
        ],
        mos_view=_mos(0.2),
        assets=None,
        monitoring=_monitoring(ThesisVerdict.BROKEN),
    )
    assert conclusion == AdvisorConclusion.RESEARCH_FURTHER


def test_expensive_quality_wait() -> None:
    conclusion = select_conclusion(
        frameworks=[
            _card(FrameworkId.GRAHAM, 55),
            _card(FrameworkId.FINANCIAL_STRENGTH, 70),
        ],
        mos_view=_mos(-0.15),
        assets=None,
        monitoring=_monitoring(ThesisVerdict.NO_CHANGE),
    )
    assert conclusion == AdvisorConclusion.WAIT


def test_strong_value_buy_more() -> None:
    conclusion = select_conclusion(
        frameworks=[
            _card(FrameworkId.GRAHAM, 75),
            _card(FrameworkId.FINANCIAL_STRENGTH, 70),
        ],
        mos_view=_mos(0.35),
        assets=None,
        monitoring=_monitoring(ThesisVerdict.STRENGTHENED),
    )
    assert conclusion == AdvisorConclusion.BUY_MORE


def test_overvalued_weak_trim() -> None:
    conclusion = select_conclusion(
        frameworks=[
            _card(FrameworkId.GRAHAM, 30),
            _card(FrameworkId.FINANCIAL_STRENGTH, 55),
        ],
        mos_view=_mos(0.05),
        assets=AssetBreakdown(
            verdict=AssetVerdict.POSSIBLE_OVERVALUATION,
            difference_pct=0.2,
        ),
        monitoring=_monitoring(ThesisVerdict.NO_CHANGE),
    )
    assert conclusion == AdvisorConclusion.TRIM


def test_insufficient_signals_research() -> None:
    conclusion = select_conclusion(
        frameworks=[
            _card(FrameworkId.GRAHAM, None),
            _card(FrameworkId.FINANCIAL_STRENGTH, None),
        ],
        mos_view=_mos(0.2),
        assets=None,
        monitoring=_monitoring(ThesisVerdict.NO_CHANGE),
    )
    assert conclusion == AdvisorConclusion.RESEARCH_FURTHER


def test_deterministic_advisor_packaging() -> None:
    insight = build_advisor(
        ticker="LITE",
        frameworks=[
            _card(FrameworkId.GRAHAM, 55),
            _card(FrameworkId.FINANCIAL_STRENGTH, 70),
        ],
        mos_view=_mos(-0.1),
        monitoring=_monitoring(ThesisVerdict.NO_CHANGE),
        mode=ThesisInsightMode.DETERMINISTIC,
    )
    assert insight.conclusion == AdvisorConclusion.WAIT
    assert insight.conclusion_label == "Wait for better entry"
    assert insight.provider == "deterministic"
    assert any("expensive" in line.lower() for line in insight.reasoning)
    assert any("no thesis change" in line.lower() for line in insight.reasoning)
    assert 0.4 <= insight.confidence <= 0.95


def test_canned_advisor_provider(tmp_path: Path) -> None:
    s = Settings(thesis_insight_mode="canned")
    insight = build_advisor(
        ticker="LITE",
        frameworks=[
            _card(FrameworkId.GRAHAM, 55),
            _card(FrameworkId.FINANCIAL_STRENGTH, 70),
        ],
        mos_view=_mos(-0.1),
        monitoring=_monitoring(ThesisVerdict.NO_CHANGE),
        app_settings=s,
    )
    assert insight.provider == "canned"
    assert insight.reasoning[-1].startswith("Guidance:")


def test_llm_fail_closed(tmp_path: Path) -> None:
    s = Settings(thesis_insight_mode="llm", google_api_key=None)
    insight = build_advisor(
        ticker="LITE",
        frameworks=[
            _card(FrameworkId.GRAHAM, 75),
            _card(FrameworkId.FINANCIAL_STRENGTH, 70),
        ],
        mos_view=_mos(0.35),
        monitoring=_monitoring(ThesisVerdict.NO_CHANGE),
        app_settings=s,
    )
    assert insight.provider == "deterministic"
    assert insight.conclusion == AdvisorConclusion.BUY_MORE


def test_explain_most_bullish() -> None:
    metrics = FinancialMetrics(
        ticker="NVDA",
        eps_trailing=5.0,
        trailing_pe=10.0,
        earnings_growth=0.10,
        total_cash=200.0,
        total_debt=80.0,
        market_cap=100.0,
        current_ratio=2.8,
        debt_to_equity=0.4,
        free_cash_flow=10.0,
        profit_margin=0.2,
        return_on_equity=0.18,
        balance_sheet=StatementSummary(total_liabilities=50.0),
        cash_flow=StatementSummary(operating_cashflow=20.0),
    )
    row = ThesisTicker(
        ticker="NVDA",
        list_kind="held",
        frameworks=scorecards_for(metrics),
    )
    ans = explain_for_row(row, question_id="most_bullish")
    assert ans.provider == "deterministic"
    lowered = ans.answer.lower()
    assert "bullish" in lowered or "scored" in lowered or "tied" in lowered
    assert ans.evidence


def test_llm_explain_fail_closed() -> None:
    row = ThesisTicker(
        ticker="NVDA",
        list_kind="held",
        frameworks=[
            _card(FrameworkId.GRAHAM, 80),
            _card(FrameworkId.FINANCIAL_STRENGTH, 60),
        ],
    )
    s = Settings(thesis_insight_mode="llm", google_api_key=None)
    ans = explain_for_row(row, question_id="framework_disagree", app_settings=s)
    assert ans.provider == "deterministic"
    assert "Graham" in ans.answer or "graham" in ans.answer.lower()


def test_llm_advisor_accepts_structured(tmp_path: Path) -> None:
    s = Settings(thesis_insight_mode="llm", google_api_key="fake", default_model="x")

    class _Resp:
        text = (
            '{"reasoning":["MoS wide.","Quality solid."],'
            '"conclusion":"buy_more","confidence":0.88}'
        )

    class _Models:
        def generate_content(self, **kwargs):
            return _Resp()

    class _Client:
        models = _Models()

    with patch("google.genai.Client", return_value=_Client()):
        insight = build_advisor(
            ticker="NVDA",
            frameworks=[
                _card(FrameworkId.GRAHAM, 75),
                _card(FrameworkId.FINANCIAL_STRENGTH, 70),
            ],
            mos_view=_mos(0.35),
            monitoring=_monitoring(ThesisVerdict.NO_CHANGE),
            app_settings=s,
        )
    assert insight.provider == "llm"
    assert insight.conclusion == AdvisorConclusion.BUY_MORE
    assert insight.confidence == 0.88

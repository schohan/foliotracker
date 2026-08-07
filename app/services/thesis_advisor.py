"""AI Portfolio Advisor (T4) — deterministic | canned | llm (fail-closed).

Directive conclusions (buy more / hold / trim / research further / wait) are
allowed **only** here. Implements architecture.md "Advisor specs" (2026-08-07).
Also powers ``POST /api/thesis/explain`` research-button answers.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.configs.settings import Settings, settings as default_settings
from app.schemas.thesis import (
    ADVISOR_CONCLUSION_LABELS,
    RESEARCH_QUESTION_IDS,
    AdvisorConclusion,
    AdvisorInsight,
    AssetBreakdown,
    AssetVerdict,
    FrameworkId,
    FrameworkScorecard,
    MarginOfSafetyView,
    ThesisExplainAnswer,
    ThesisInsightMode,
    ThesisMonitoring,
    ThesisTicker,
    ThesisVerdict,
)
from app.services.thesis_insight import parse_insight_mode

logger = logging.getLogger(__name__)

# Locked thresholds (architecture.md Advisor specs)
_MOS_STRONG = 0.30
_MOS_EXPENSIVE = 0.0
_FRAMEWORK_STRONG = 60.0
_FRAMEWORK_WEAK = 40.0
_FRAMEWORK_OK = 50.0
_MIN_KNOWN_SIGNALS = 2


def _score_for(
    frameworks: list[FrameworkScorecard], framework: FrameworkId
) -> float | None:
    for card in frameworks:
        if card.framework == framework:
            return card.score
    return None


def _fmt_pct(frac: float) -> str:
    return f"{frac * 100:.0f}%"


def _fmt_score(score: float) -> str:
    return f"{score:.0f}"


def build_reasoning(
    *,
    ticker: str,
    frameworks: list[FrameworkScorecard],
    mos_view: MarginOfSafetyView | None,
    assets: AssetBreakdown | None,
    monitoring: ThesisMonitoring | None,
) -> list[str]:
    """Deterministic reasoning lines (PRD §5.4.5 style)."""
    lines: list[str] = []
    graham = _score_for(frameworks, FrameworkId.GRAHAM)
    fs = _score_for(frameworks, FrameworkId.FINANCIAL_STRENGTH)
    mos = mos_view.margin_of_safety if mos_view is not None else None

    if mos is not None:
        if mos < _MOS_EXPENSIVE:
            lines.append(f"{ticker} remains expensive (MoS {_fmt_pct(mos)}).")
        elif mos >= _MOS_STRONG:
            lines.append(f"{ticker} offers a wide margin of safety ({_fmt_pct(mos)}).")
        else:
            lines.append(f"Valuation MoS is {_fmt_pct(mos)}.")
    else:
        lines.append(f"{ticker}: margin of safety insufficient data.")

    if fs is not None:
        if fs >= _FRAMEWORK_STRONG:
            lines.append(f"Business quality looks solid (Financial Strength {_fmt_score(fs)}).")
        elif fs < _FRAMEWORK_WEAK:
            lines.append(f"Financial Strength is weak ({_fmt_score(fs)}).")
        else:
            lines.append(f"Financial Strength is mixed ({_fmt_score(fs)}).")

    if graham is not None:
        if graham >= _FRAMEWORK_STRONG:
            lines.append(f"Graham Deep Value score is strong ({_fmt_score(graham)}).")
        elif graham < _FRAMEWORK_WEAK:
            lines.append(f"Graham Deep Value score is weak ({_fmt_score(graham)}).")
        else:
            lines.append(f"Graham Deep Value score is {_fmt_score(graham)}.")

    if assets is not None and assets.verdict is not None:
        if assets.verdict == AssetVerdict.POSSIBLE_OVERVALUATION:
            lines.append("Market value sits above adjusted net assets.")
        elif assets.verdict == AssetVerdict.POSSIBLE_UNDERVALUATION:
            lines.append("Adjusted net assets exceed market value.")

    verdict = (
        monitoring.current.verdict
        if monitoring is not None and monitoring.current is not None
        else None
    )
    if verdict == ThesisVerdict.NO_CHANGE:
        lines.append("No thesis change.")
    elif verdict == ThesisVerdict.STRENGTHENED:
        lines.append("Thesis strengthened versus the prior quarter.")
    elif verdict == ThesisVerdict.SLIGHTLY_WEAKER:
        lines.append("Thesis slightly weaker versus the prior quarter.")
    elif verdict == ThesisVerdict.BROKEN:
        lines.append("Thesis signals crossed a Broken threshold.")

    return lines


def select_conclusion(
    *,
    frameworks: list[FrameworkScorecard],
    mos_view: MarginOfSafetyView | None,
    assets: AssetBreakdown | None,
    monitoring: ThesisMonitoring | None,
) -> AdvisorConclusion:
    """Priority table from architecture.md Advisor specs (first match wins)."""
    graham = _score_for(frameworks, FrameworkId.GRAHAM)
    fs = _score_for(frameworks, FrameworkId.FINANCIAL_STRENGTH)
    mos = mos_view.margin_of_safety if mos_view is not None else None
    verdict = (
        monitoring.current.verdict
        if monitoring is not None and monitoring.current is not None
        else None
    )

    known = sum(1 for v in (graham, fs, mos) if v is not None)

    if verdict == ThesisVerdict.BROKEN:
        return AdvisorConclusion.RESEARCH_FURTHER

    if known < _MIN_KNOWN_SIGNALS:
        return AdvisorConclusion.RESEARCH_FURTHER

    if verdict == ThesisVerdict.SLIGHTLY_WEAKER:
        if mos is not None and mos >= _MOS_EXPENSIVE:
            return AdvisorConclusion.HOLD
        return AdvisorConclusion.RESEARCH_FURTHER

    # Expensive with at-least-ok quality → wait
    quality_ok = (fs is not None and fs >= _FRAMEWORK_OK) or (
        graham is not None and graham >= _FRAMEWORK_OK
    )
    if mos is not None and mos < _MOS_EXPENSIVE and quality_ok:
        return AdvisorConclusion.WAIT

    # Overvalued assets + weak frameworks → trim
    weak_fw = (graham is not None and graham < _FRAMEWORK_WEAK) or (
        fs is not None and fs < _FRAMEWORK_WEAK
    )
    if (
        assets is not None
        and assets.verdict == AssetVerdict.POSSIBLE_OVERVALUATION
        and weak_fw
    ):
        return AdvisorConclusion.TRIM

    # Strong value entry
    known_scores = [s for s in (graham, fs) if s is not None]
    avg_fw = sum(known_scores) / len(known_scores) if known_scores else None
    healthy_verdict = verdict in (
        None,
        ThesisVerdict.NO_CHANGE,
        ThesisVerdict.STRENGTHENED,
    )
    if (
        mos is not None
        and mos >= _MOS_STRONG
        and avg_fw is not None
        and avg_fw >= _FRAMEWORK_STRONG
        and healthy_verdict
    ):
        return AdvisorConclusion.BUY_MORE

    if mos is not None and mos >= _MOS_EXPENSIVE and healthy_verdict:
        return AdvisorConclusion.HOLD

    return AdvisorConclusion.RESEARCH_FURTHER


def compute_confidence(
    *,
    frameworks: list[FrameworkScorecard],
    mos_view: MarginOfSafetyView | None,
    assets: AssetBreakdown | None,
    monitoring: ThesisMonitoring | None,
) -> float:
    """Coverage-based confidence in [0.40, 0.95]."""
    graham = _score_for(frameworks, FrameworkId.GRAHAM)
    fs = _score_for(frameworks, FrameworkId.FINANCIAL_STRENGTH)
    mos = mos_view.margin_of_safety if mos_view is not None else None
    conf = 0.50
    for present in (graham is not None, fs is not None, mos is not None):
        if present:
            conf += 0.10
    if assets is not None and assets.verdict is not None:
        conf += 0.05
    if (
        monitoring is not None
        and monitoring.current is not None
        and monitoring.current.evidence
        and monitoring.current.evidence[0] != "baseline — no prior quarter"
    ):
        conf += 0.05
    return max(0.40, min(0.95, round(conf, 2)))


def _pack(
    reasoning: list[str],
    conclusion: AdvisorConclusion,
    confidence: float,
    provider: ThesisInsightMode,
) -> AdvisorInsight:
    return AdvisorInsight(
        reasoning=reasoning,
        conclusion=conclusion,
        conclusion_label=ADVISOR_CONCLUSION_LABELS[conclusion],
        confidence=confidence,
        provider=provider.value,
    )


def deterministic_advisor(
    *,
    ticker: str,
    frameworks: list[FrameworkScorecard],
    mos_view: MarginOfSafetyView | None = None,
    assets: AssetBreakdown | None = None,
    monitoring: ThesisMonitoring | None = None,
) -> AdvisorInsight:
    reasoning = build_reasoning(
        ticker=ticker,
        frameworks=frameworks,
        mos_view=mos_view,
        assets=assets,
        monitoring=monitoring,
    )
    conclusion = select_conclusion(
        frameworks=frameworks,
        mos_view=mos_view,
        assets=assets,
        monitoring=monitoring,
    )
    confidence = compute_confidence(
        frameworks=frameworks,
        mos_view=mos_view,
        assets=assets,
        monitoring=monitoring,
    )
    return _pack(reasoning, conclusion, confidence, ThesisInsightMode.DETERMINISTIC)


def canned_advisor(
    *,
    ticker: str,
    frameworks: list[FrameworkScorecard],
    mos_view: MarginOfSafetyView | None = None,
    assets: AssetBreakdown | None = None,
    monitoring: ThesisMonitoring | None = None,
) -> AdvisorInsight:
    base = deterministic_advisor(
        ticker=ticker,
        frameworks=frameworks,
        mos_view=mos_view,
        assets=assets,
        monitoring=monitoring,
    )
    # Same conclusion/confidence; slightly warmer closing line.
    label = base.conclusion_label
    extra = f"Guidance: {label} — review the evidence before acting."
    reasoning = list(base.reasoning) + [extra]
    return _pack(
        reasoning,
        base.conclusion,
        base.confidence,
        ThesisInsightMode.CANNED,
    )


def _extract_json_object(raw: str) -> dict[str, Any] | None:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None


def _parse_conclusion(raw: Any) -> AdvisorConclusion | None:
    if not isinstance(raw, str):
        return None
    key = raw.strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "buy": AdvisorConclusion.BUY_MORE,
        "buy_more": AdvisorConclusion.BUY_MORE,
        "hold": AdvisorConclusion.HOLD,
        "trim": AdvisorConclusion.TRIM,
        "research": AdvisorConclusion.RESEARCH_FURTHER,
        "research_further": AdvisorConclusion.RESEARCH_FURTHER,
        "wait": AdvisorConclusion.WAIT,
        "wait_for_better_entry": AdvisorConclusion.WAIT,
    }
    return aliases.get(key)


def llm_advisor(
    *,
    ticker: str,
    frameworks: list[FrameworkScorecard],
    mos_view: MarginOfSafetyView | None,
    assets: AssetBreakdown | None,
    monitoring: ThesisMonitoring | None,
    app_settings: Settings,
) -> AdvisorInsight | None:
    """Gemini structured advisor; None on failure (fail-closed)."""
    api_key = app_settings.google_api_key
    if not api_key:
        logger.info("thesis_advisor_llm_skip reason=no_api_key")
        return None

    det = deterministic_advisor(
        ticker=ticker,
        frameworks=frameworks,
        mos_view=mos_view,
        assets=assets,
        monitoring=monitoring,
    )
    allowed = ", ".join(c.value for c in AdvisorConclusion)
    prompt = (
        "You are FolioTracker's AI Portfolio Advisor. Return ONLY JSON with keys: "
        "reasoning (array of short strings), conclusion (one of: "
        f"{allowed}), confidence (0-1 float). "
        "Directive conclusions are allowed here only. Always ground reasoning in "
        "the supplied signals; do not invent numbers. "
        f"Ticker={ticker} deterministic_seed={det.model_dump()!r}"
    )
    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=app_settings.default_model,
            contents=prompt,
        )
        raw = getattr(response, "text", None) or ""
        data = _extract_json_object(raw)
        if not data:
            logger.info("thesis_advisor_llm_parse_fail ticker=%s", ticker)
            return None
        conclusion = _parse_conclusion(data.get("conclusion"))
        reasoning_raw = data.get("reasoning")
        if conclusion is None or not isinstance(reasoning_raw, list):
            return None
        reasoning = [str(x).strip()[:200] for x in reasoning_raw if str(x).strip()][:8]
        if not reasoning:
            return None
        try:
            confidence = float(data.get("confidence", det.confidence))
        except (TypeError, ValueError):
            confidence = det.confidence
        confidence = max(0.0, min(1.0, round(confidence, 2)))
        return _pack(reasoning, conclusion, confidence, ThesisInsightMode.LLM)
    except Exception as exc:  # noqa: BLE001 — fail-closed
        logger.info(
            "thesis_advisor_llm_fail ticker=%s err=%s",
            ticker,
            exc.__class__.__name__,
        )
        return None


def build_advisor(
    *,
    ticker: str,
    frameworks: list[FrameworkScorecard],
    mos_view: MarginOfSafetyView | None = None,
    assets: AssetBreakdown | None = None,
    monitoring: ThesisMonitoring | None = None,
    mode: ThesisInsightMode | str | None = None,
    app_settings: Settings | None = None,
) -> AdvisorInsight:
    """Build advisor insight; llm fails closed to deterministic."""
    s = app_settings if app_settings is not None else default_settings
    if mode is None:
        resolved = parse_insight_mode(getattr(s, "thesis_insight_mode", "deterministic"))
    elif isinstance(mode, ThesisInsightMode):
        resolved = mode
    else:
        resolved = parse_insight_mode(str(mode))

    kwargs = dict(
        ticker=ticker,
        frameworks=frameworks,
        mos_view=mos_view,
        assets=assets,
        monitoring=monitoring,
    )
    if resolved == ThesisInsightMode.CANNED:
        return canned_advisor(**kwargs)
    if resolved == ThesisInsightMode.LLM:
        llm = llm_advisor(**kwargs, app_settings=s)
        if llm is not None:
            return llm
        return deterministic_advisor(**kwargs)
    return deterministic_advisor(**kwargs)


# --- Research button (POST /api/thesis/explain) ---------------------------------


def resolve_question(question_id: str, question: str) -> tuple[str, str]:
    """Return (question_id, question_text)."""
    qid = (question_id or "").strip().lower()
    free = (question or "").strip()
    if qid and qid in RESEARCH_QUESTION_IDS:
        return qid, RESEARCH_QUESTION_IDS[qid]
    if free:
        return qid or "custom", free
    # Default to most-bullish when neither provided
    default_id = "most_bullish"
    return default_id, RESEARCH_QUESTION_IDS[default_id]


def _framework_disagree_answer(row: ThesisTicker) -> tuple[str, list[str]]:
    graham = _score_for(row.frameworks, FrameworkId.GRAHAM)
    fs = _score_for(row.frameworks, FrameworkId.FINANCIAL_STRENGTH)
    evidence: list[str] = []
    if graham is not None:
        evidence.append(f"graham_score={_fmt_score(graham)}")
    if fs is not None:
        evidence.append(f"fs_score={_fmt_score(fs)}")
    if graham is None and fs is None:
        return (
            "Both Graham and Financial Strength lack enough inputs to score — "
            "insufficient data, not disagreement.",
            evidence,
        )
    if graham is None:
        return (
            f"Graham is unscored (insufficient data) while Financial Strength is "
            f"{_fmt_score(fs)} — the gap is coverage, not a true framework conflict.",
            evidence,
        )
    if fs is None:
        return (
            f"Financial Strength is unscored while Graham is {_fmt_score(graham)} — "
            "the gap is coverage, not a true framework conflict.",
            evidence,
        )
    delta = abs(graham - fs)
    if delta < 10:
        return (
            f"Graham ({_fmt_score(graham)}) and Financial Strength ({_fmt_score(fs)}) "
            "are close — no material disagreement.",
            evidence,
        )
    if graham > fs:
        return (
            f"Graham ({_fmt_score(graham)}) outscores Financial Strength "
            f"({_fmt_score(fs)}). Deep-value MoS/earnings checks can look fine while "
            "leverage or cash-flow checks drag Financial Strength down.",
            evidence,
        )
    return (
        f"Financial Strength ({_fmt_score(fs)}) outscores Graham "
        f"({_fmt_score(graham)}). Balance-sheet quality can look solid while "
        "Graham's price-vs-intrinsic MoS remains thin or negative.",
        evidence,
    )


def _mos_change_answer(row: ThesisTicker) -> tuple[str, list[str]]:
    mos = row.margin_of_safety
    evidence: list[str] = []
    if mos is None or mos.margin_of_safety is None:
        return (
            "Margin of Safety is insufficient data right now — no move to explain.",
            evidence,
        )
    evidence.append(f"mos={_fmt_pct(mos.margin_of_safety)}")
    if mos.intrinsic_value is not None:
        evidence.append(f"intrinsic={mos.intrinsic_value:.2f}")
    if mos.market_price is not None:
        evidence.append(f"market_price={mos.market_price:.2f}")
    current = (
        row.monitoring.current
        if row.monitoring is not None
        else None
    )
    if current is not None:
        mos_lines = [e for e in current.evidence if e.startswith("mos ")]
        if mos_lines:
            evidence.extend(mos_lines[:2])
            return (
                f"Current MoS is {_fmt_pct(mos.margin_of_safety)} "
                f"({mos.rating or 'unrated'}). Cited delta: {mos_lines[0]}.",
                evidence,
            )
    return (
        f"Current MoS is {_fmt_pct(mos.margin_of_safety)} "
        f"({mos.rating or 'unrated'}). No quarterly MoS delta is cited yet "
        "(baseline or unchanged).",
        evidence,
    )


def _most_bullish_answer(row: ThesisTicker) -> tuple[str, list[str]]:
    scored = [(c.label, c.score) for c in row.frameworks if c.score is not None]
    evidence = [f"{label}={_fmt_score(score)}" for label, score in scored]
    if not scored:
        return (
            "No framework has enough coverage to score — cannot pick a bullish lens.",
            evidence,
        )
    scored.sort(key=lambda x: x[1], reverse=True)
    best_label, best_score = scored[0]
    if len(scored) == 1:
        return (
            f"{best_label} is the only scored framework ({_fmt_score(best_score)}).",
            evidence,
        )
    second_label, second_score = scored[1]
    if abs(best_score - second_score) < 1:
        return (
            f"{best_label} and {second_label} are essentially tied "
            f"({_fmt_score(best_score)}).",
            evidence,
        )
    return (
        f"{best_label} is most bullish at {_fmt_score(best_score)} "
        f"(vs {second_label} {_fmt_score(second_score)}).",
        evidence,
    )


def _custom_answer(row: ThesisTicker, question: str) -> tuple[str, list[str]]:
    graham = _score_for(row.frameworks, FrameworkId.GRAHAM)
    fs = _score_for(row.frameworks, FrameworkId.FINANCIAL_STRENGTH)
    mos = (
        row.margin_of_safety.margin_of_safety
        if row.margin_of_safety is not None
        else None
    )
    bits = [
        f"Q: {question}",
        f"Graham={_fmt_score(graham) if graham is not None else '—'}",
        f"FS={_fmt_score(fs) if fs is not None else '—'}",
        f"MoS={_fmt_pct(mos) if mos is not None else '—'}",
    ]
    if row.advisor is not None:
        bits.append(
            f"Advisor={row.advisor.conclusion_label} "
            f"({row.advisor.confidence:.0%} conf)"
        )
    return (
        "Deterministic summary of current thesis signals (not free-form research): "
        + "; ".join(bits[1:])
        + ".",
        bits,
    )


def deterministic_explain(row: ThesisTicker, question_id: str, question: str) -> ThesisExplainAnswer:
    if question_id == "framework_disagree":
        answer, evidence = _framework_disagree_answer(row)
    elif question_id == "mos_change":
        answer, evidence = _mos_change_answer(row)
    elif question_id == "most_bullish":
        answer, evidence = _most_bullish_answer(row)
    else:
        answer, evidence = _custom_answer(row, question)
    return ThesisExplainAnswer(
        ticker=row.ticker,
        question_id=question_id,
        question=question,
        answer=answer,
        evidence=evidence,
        provider=ThesisInsightMode.DETERMINISTIC.value,
    )


def canned_explain(row: ThesisTicker, question_id: str, question: str) -> ThesisExplainAnswer:
    base = deterministic_explain(row, question_id, question)
    return base.model_copy(
        update={
            "answer": f"{base.answer} Dig into the cited scorecards before deciding.",
            "provider": ThesisInsightMode.CANNED.value,
        }
    )


def llm_explain(
    row: ThesisTicker,
    question_id: str,
    question: str,
    *,
    app_settings: Settings,
) -> ThesisExplainAnswer | None:
    api_key = app_settings.google_api_key
    if not api_key:
        return None
    seed = deterministic_explain(row, question_id, question)
    prompt = (
        "Answer one FolioTracker research question. Return ONLY JSON with keys "
        "answer (string ≤500 chars) and evidence (array of short strings). "
        "Do not invent numbers; ground in the seed. "
        "You may explain frameworks; do not give a new buy/sell order beyond "
        "restating the existing advisor conclusion if present. "
        f"Ticker={row.ticker} question={question!r} seed={seed.model_dump()!r}"
    )
    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=app_settings.default_model,
            contents=prompt,
        )
        raw = getattr(response, "text", None) or ""
        data = _extract_json_object(raw)
        if not data or not isinstance(data.get("answer"), str):
            return None
        answer = str(data["answer"]).strip()[:500]
        if not answer:
            return None
        evidence_raw = data.get("evidence")
        evidence = (
            [str(x).strip()[:120] for x in evidence_raw if str(x).strip()][:8]
            if isinstance(evidence_raw, list)
            else list(seed.evidence)
        )
        return ThesisExplainAnswer(
            ticker=row.ticker,
            question_id=question_id,
            question=question,
            answer=answer,
            evidence=evidence,
            provider=ThesisInsightMode.LLM.value,
        )
    except Exception as exc:  # noqa: BLE001
        logger.info(
            "thesis_explain_llm_fail ticker=%s err=%s",
            row.ticker,
            exc.__class__.__name__,
        )
        return None


def explain_for_row(
    row: ThesisTicker,
    *,
    question_id: str = "",
    question: str = "",
    mode: ThesisInsightMode | str | None = None,
    app_settings: Settings | None = None,
) -> ThesisExplainAnswer:
    """Research-button answer; llm fails closed to deterministic."""
    s = app_settings if app_settings is not None else default_settings
    qid, qtext = resolve_question(question_id, question)
    if mode is None:
        resolved = parse_insight_mode(getattr(s, "thesis_insight_mode", "deterministic"))
    elif isinstance(mode, ThesisInsightMode):
        resolved = mode
    else:
        resolved = parse_insight_mode(str(mode))

    if resolved == ThesisInsightMode.CANNED:
        return canned_explain(row, qid, qtext)
    if resolved == ThesisInsightMode.LLM:
        llm = llm_explain(row, qid, qtext, app_settings=s)
        if llm is not None:
            return llm
        return deterministic_explain(row, qid, qtext)
    return deterministic_explain(row, qid, qtext)

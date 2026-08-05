"""Brief insight provider — deterministic | canned | llm (fail-closed)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.configs.settings import Settings, settings as default_settings
from app.schemas.brief import (
    BriefEventCategory,
    BriefInsight,
    BriefInsightMode,
    BriefSentiment,
)

logger = logging.getLogger(__name__)

_CANNED_BY_CATEGORY: dict[BriefEventCategory, dict[str, str]] = {
    BriefEventCategory.ANALYST_RATING: {
        "what_happened": "Analyst rating or target change on this name.",
        "why": "Street expectations may shift; near-term flows often follow upgrades/downgrades.",
        "market_reaction": "Check pre-market / session move vs peers.",
        "should_long_term_care": "YES if the thesis hinges on growth narrative; MAYBE otherwise.",
        "confidence_label": "Medium",
        "suggested_action": "Read the note if Held > equal-weight slice of the book.",
        "explain_busy": "An analyst changed their view. That can move the stock short-term; long-term it matters only if it changes earnings power assumptions you already believe.",
    },
    BriefEventCategory.EARNINGS_GUIDANCE: {
        "what_happened": "Earnings results or guidance update.",
        "why": "Revises the fundamental path that long-term holders care about.",
        "market_reaction": "Gap moves are common around prints; compare to estimate surprise if known.",
        "should_long_term_care": "YES",
        "confidence_label": "High",
        "suggested_action": "Read the release / transcript before the next session if Held.",
        "explain_busy": "The company reported or guided. Numbers and outlook drive thesis validity more than day-to-day headlines.",
    },
    BriefEventCategory.SECURITY_BREACH: {
        "what_happened": "Security or cyber incident reported.",
        "why": "Can imply costs, liability, and trust damage beyond one trading day.",
        "market_reaction": "Often sells off until scope is clear.",
        "should_long_term_care": "YES",
        "confidence_label": "Medium",
        "suggested_action": "Assess scope and disclosure; review thesis risk if Held.",
        "explain_busy": "A breach can become a real cost and reputation hit. Confirm facts from primary filings or company PR before acting on headlines.",
    },
    BriefEventCategory.CONTRACTS_WON_LOST: {
        "what_happened": "Material contract win or loss.",
        "why": "May change near-term revenue visibility.",
        "market_reaction": "Wins often lift; losses can pressure.",
        "should_long_term_care": "MAYBE",
        "confidence_label": "Medium",
        "suggested_action": "Confirm size and duration vs existing backlog narrative.",
        "explain_busy": "A large deal can matter if it is material to revenue. Verify size relative to the company's scale before treating it as thesis-changing.",
    },
    BriefEventCategory.REGULATORY_MATERIAL: {
        "what_happened": "Regulatory, legal, or filing-driven development.",
        "why": "Rules, probes, or material filings can alter risk and timing.",
        "market_reaction": "Binary headlines can whip price until details land.",
        "should_long_term_care": "YES",
        "confidence_label": "Medium",
        "suggested_action": "Open the SEC / primary filing; skim risk factors update.",
        "explain_busy": "Regulators or courts moved something that may change the company's risk. Prefer primary filings over secondary headlines.",
    },
    BriefEventCategory.PRODUCT_ANNOUNCEMENT: {
        "what_happened": "Product or launch announcement.",
        "why": "Can support growth narrative if commercially meaningful.",
        "market_reaction": "Often modest unless tied to revenue guidance.",
        "should_long_term_care": "MAYBE",
        "confidence_label": "Low",
        "suggested_action": "Note for thesis; skip deep dive unless Held and core product.",
        "explain_busy": "A product headline is noise unless it changes expected revenue or margins. Skim once; dig only if it is core to why you own it.",
    },
    BriefEventCategory.OTHER_MATERIAL: {
        "what_happened": "Press item flagged as potentially material.",
        "why": "Classifier marked it; verify before acting.",
        "market_reaction": "Varies widely.",
        "should_long_term_care": "MAYBE",
        "confidence_label": "Low",
        "suggested_action": "Skim source; escalate only if it touches thesis risks.",
        "explain_busy": "This might matter, or it might be filler. Open the source, decide in thirty seconds, and move on if it is not thesis-relevant.",
    },
    BriefEventCategory.PRICE_MOVE: {
        "what_happened": "Large session price move without a classified headline.",
        "why": "Something moved the stock; cause may still be unknown.",
        "market_reaction": "Session move already visible in daily return.",
        "should_long_term_care": "MAYBE",
        "confidence_label": "Low",
        "suggested_action": "Scan peers and primary sources for a catalyst.",
        "explain_busy": "The stock moved a lot. Until you know why, treat it as a prompt to find the catalyst — not as a thesis conclusion.",
    },
}


def parse_insight_mode(raw: str | None) -> BriefInsightMode:
    try:
        return BriefInsightMode((raw or "deterministic").strip().lower())
    except ValueError:
        return BriefInsightMode.DETERMINISTIC


def _fmt_pct(daily_return: float | None) -> str:
    if daily_return is None:
        return "Move not available"
    pct = daily_return * 100
    sign = "+" if pct > 0 else ""
    return f"Session {sign}{pct:.1f}%"


def _care_label(
    *,
    list_kind: str,
    category: BriefEventCategory,
    sentiment: BriefSentiment,
    impact: int,
) -> str:
    if list_kind == "held" and impact >= 80:
        return "YES"
    if category in (
        BriefEventCategory.EARNINGS_GUIDANCE,
        BriefEventCategory.SECURITY_BREACH,
        BriefEventCategory.REGULATORY_MATERIAL,
    ):
        return "YES" if list_kind == "held" else "MAYBE"
    if sentiment == BriefSentiment.NEGATIVE and impact >= 70:
        return "YES" if list_kind == "held" else "MAYBE"
    return "MAYBE" if list_kind == "held" else "NO"


def _action_for(
    category: BriefEventCategory,
    *,
    list_kind: str,
    sentiment: BriefSentiment,
) -> str:
    if category == BriefEventCategory.EARNINGS_GUIDANCE:
        return (
            "Read earnings notes before market opens"
            if list_kind == "held"
            else "Skim results; decide promote / ignore"
        )
    if category == BriefEventCategory.ANALYST_RATING:
        return "Read report if Held; otherwise note Street shift"
    if category == BriefEventCategory.SECURITY_BREACH:
        return "Review thesis risk; confirm scope from primary source"
    if category == BriefEventCategory.REGULATORY_MATERIAL:
        return "Open filing; check whether risk factors changed"
    if category == BriefEventCategory.PRICE_MOVE:
        return "Find catalyst; compare vs sector peers"
    if sentiment == BriefSentiment.NEGATIVE:
        return "Review thesis if Held; monitor if Watched"
    return "Skim source; no trade action suggested"


def deterministic_insight(
    *,
    ticker: str,
    category: BriefEventCategory,
    text: str,
    list_kind: str,
    daily_return: float | None,
    sentiment: BriefSentiment,
    impact: int,
    confidence: int,
) -> BriefInsight:
    headline = (text or "").strip() or category_headline_fallback(category)
    care = _care_label(
        list_kind=list_kind,
        category=category,
        sentiment=sentiment,
        impact=impact,
    )
    action = _action_for(category, list_kind=list_kind, sentiment=sentiment)
    conf_label = (
        "High" if confidence >= 75 else "Medium" if confidence >= 50 else "Low"
    )
    why = {
        BriefEventCategory.EARNINGS_GUIDANCE: "Results or guidance can revise fundamentals.",
        BriefEventCategory.ANALYST_RATING: "Street target/rating shifts can move near-term flows.",
        BriefEventCategory.SECURITY_BREACH: "Incidents can imply cost, liability, and trust damage.",
        BriefEventCategory.CONTRACTS_WON_LOST: "Deal flow may change revenue visibility.",
        BriefEventCategory.REGULATORY_MATERIAL: "Regulatory or legal items can change risk timing.",
        BriefEventCategory.PRODUCT_ANNOUNCEMENT: "Product news matters if commercially material.",
        BriefEventCategory.OTHER_MATERIAL: "Flagged as potentially material — verify source.",
        BriefEventCategory.PRICE_MOVE: "Large move without a clear classified headline.",
    }.get(category, "Potentially material to the name.")

    explain = (
        f"{ticker}: {headline[:120]}. "
        f"{why} "
        f"Suggested: {action}."
    )
    return BriefInsight(
        what_happened=headline[:200],
        why=why,
        market_reaction=_fmt_pct(daily_return),
        should_long_term_care=care,
        confidence_label=conf_label,
        suggested_action=action,
        explain_busy=explain,
        provider=BriefInsightMode.DETERMINISTIC,
    )


def category_headline_fallback(category: BriefEventCategory) -> str:
    from app.services.brief_impact import category_headline

    return category_headline(category)


def canned_insight(
    *,
    ticker: str,
    category: BriefEventCategory,
    text: str,
    list_kind: str,
    daily_return: float | None,
    sentiment: BriefSentiment,
    impact: int,
    confidence: int,
) -> BriefInsight:
    base = _CANNED_BY_CATEGORY.get(
        category, _CANNED_BY_CATEGORY[BriefEventCategory.OTHER_MATERIAL]
    )
    action = _action_for(category, list_kind=list_kind, sentiment=sentiment)
    care = _care_label(
        list_kind=list_kind,
        category=category,
        sentiment=sentiment,
        impact=impact,
    )
    conf_label = (
        "High" if confidence >= 75 else "Medium" if confidence >= 50 else "Low"
    )
    what = (text or "").strip() or base["what_happened"]
    return BriefInsight(
        what_happened=what[:200],
        why=base["why"],
        market_reaction=_fmt_pct(daily_return) if daily_return is not None else base["market_reaction"],
        should_long_term_care=care,
        confidence_label=conf_label,
        suggested_action=action or base["suggested_action"],
        explain_busy=f"{ticker}: {base['explain_busy']}",
        provider=BriefInsightMode.CANNED,
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


def llm_insight(
    *,
    ticker: str,
    category: BriefEventCategory,
    text: str,
    list_kind: str,
    daily_return: float | None,
    sentiment: BriefSentiment,
    impact: int,
    confidence: int,
    app_settings: Settings,
) -> BriefInsight | None:
    """Call Gemini for structured insight; return None on any failure."""
    api_key = app_settings.google_api_key
    if not api_key:
        logger.info("brief_llm_skip reason=no_api_key")
        return None
    prompt = (
        "You are a portfolio triage assistant. Return ONLY JSON with keys: "
        "what_happened, why, market_reaction, should_long_term_care, "
        "confidence_label, suggested_action, explain_busy. "
        "No buy/sell advice. Actions must be read/review/monitor style. "
        f"Ticker={ticker} list={list_kind} category={category.value} "
        f"impact={impact} sentiment={sentiment.value} "
        f"daily_return={daily_return} headline={text!r}"
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
            logger.info("brief_llm_parse_fail ticker=%s", ticker)
            return None
        required = (
            "what_happened",
            "why",
            "market_reaction",
            "should_long_term_care",
            "confidence_label",
            "suggested_action",
            "explain_busy",
        )
        if not all(isinstance(data.get(k), str) and data.get(k) for k in required):
            return None
        # Reject advice-looking language.
        joined = " ".join(str(data[k]) for k in required).lower()
        if any(x in joined for x in ("buy now", "sell now", "trim to", "add shares")):
            logger.info("brief_llm_reject_advice ticker=%s", ticker)
            return None
        return BriefInsight(
            what_happened=str(data["what_happened"])[:300],
            why=str(data["why"])[:400],
            market_reaction=str(data["market_reaction"])[:200],
            should_long_term_care=str(data["should_long_term_care"])[:40],
            confidence_label=str(data["confidence_label"])[:40],
            suggested_action=str(data["suggested_action"])[:200],
            explain_busy=str(data["explain_busy"])[:500],
            provider=BriefInsightMode.LLM,
        )
    except Exception as exc:  # noqa: BLE001 — fail-closed
        logger.info("brief_llm_fail ticker=%s err=%s", ticker, exc.__class__.__name__)
        return None


def build_insight(
    *,
    ticker: str,
    category: BriefEventCategory,
    text: str,
    list_kind: str,
    daily_return: float | None,
    sentiment: BriefSentiment,
    impact: int,
    confidence: int,
    mode: BriefInsightMode | str | None = None,
    app_settings: Settings | None = None,
) -> BriefInsight:
    """Build insight for the configured provider; llm fails closed to deterministic."""
    s = app_settings if app_settings is not None else default_settings
    if mode is None:
        resolved = parse_insight_mode(getattr(s, "brief_insight_mode", "deterministic"))
    elif isinstance(mode, BriefInsightMode):
        resolved = mode
    else:
        resolved = parse_insight_mode(str(mode))

    kwargs = dict(
        ticker=ticker,
        category=category,
        text=text,
        list_kind=list_kind,
        daily_return=daily_return,
        sentiment=sentiment,
        impact=impact,
        confidence=confidence,
    )
    if resolved == BriefInsightMode.CANNED:
        return canned_insight(**kwargs)
    if resolved == BriefInsightMode.LLM:
        llm = llm_insight(**kwargs, app_settings=s)
        if llm is not None:
            return llm
        fallback = deterministic_insight(**kwargs)
        return fallback.model_copy(update={"provider": BriefInsightMode.DETERMINISTIC})
    return deterministic_insight(**kwargs)


def why_it_matters_bullets(
    *,
    category: BriefEventCategory,
    list_kind: str,
    sentiment: BriefSentiment,
    daily_return: float | None,
) -> list[str]:
    lines: list[str] = []
    if category == BriefEventCategory.EARNINGS_GUIDANCE:
        lines.append("Earnings or guidance can revise the fundamental path")
    elif category == BriefEventCategory.ANALYST_RATING:
        lines.append("Street rating/target changes can shift near-term flows")
    elif category == BriefEventCategory.SECURITY_BREACH:
        lines.append("Incidents can imply cost, liability, and trust damage")
    elif category == BriefEventCategory.REGULATORY_MATERIAL:
        lines.append("Regulatory or legal items can change risk and timing")
    elif category == BriefEventCategory.CONTRACTS_WON_LOST:
        lines.append("Contract flow may change revenue visibility")
    elif category == BriefEventCategory.PRODUCT_ANNOUNCEMENT:
        lines.append("Product news matters if commercially material")
    elif category == BriefEventCategory.PRICE_MOVE:
        lines.append("Large move without a classified headline — catalyst unknown")
    else:
        lines.append("Flagged as potentially material — verify before acting")

    if list_kind == "held":
        lines.append("You hold this name (equal-weight Held book)")
    else:
        lines.append("On Watched — relevant for promote / add, not Held capital")

    if daily_return is not None and abs(daily_return) >= 0.05:
        lines.append(_fmt_pct(daily_return))
    elif sentiment != BriefSentiment.NEUTRAL:
        lines.append(f"Tone reads {sentiment.value}")
    return lines[:4]


def confidence_for_event(
    *,
    category: BriefEventCategory,
    has_source_url: bool,
    severity: int,
) -> int:
    base = 55 + (severity - 3) * 8
    if has_source_url:
        base += 10
    if category in (
        BriefEventCategory.EARNINGS_GUIDANCE,
        BriefEventCategory.REGULATORY_MATERIAL,
    ):
        base += 8
    if category in (
        BriefEventCategory.OTHER_MATERIAL,
        BriefEventCategory.PRICE_MOVE,
    ):
        base -= 10
    return max(20, min(95, base))

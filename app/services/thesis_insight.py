"""Thesis change narrative — deterministic | canned | llm (fail-closed).

T3: fills ``ThesisChange.narrative`` only. No directive buy/sell/trim/wait
phrasing (Advisor-only, T4). Mirrors brief_insight provider pattern.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.configs.settings import Settings, settings as default_settings
from app.schemas.thesis import (
    THESIS_VERDICT_LABELS,
    ThesisChange,
    ThesisInsightMode,
    ThesisVerdict,
)

logger = logging.getLogger(__name__)

_DIRECTIVE_NEEDLES = (
    "buy now",
    "sell now",
    "buy more",
    "sell all",
    "trim to",
    "add shares",
    "go long",
    "go short",
    "wait for better entry",
)

_CANNED: dict[ThesisVerdict, str] = {
    ThesisVerdict.NO_CHANGE: (
        "Thesis posture is steady versus the prior quarter. "
        "Signal deltas stay within the locked no-change band."
    ),
    ThesisVerdict.STRENGTHENED: (
        "Thesis looks stronger on the deterministic scorecard and/or margin of safety. "
        "Review the cited deltas; this is not a trade recommendation."
    ),
    ThesisVerdict.SLIGHTLY_WEAKER: (
        "Thesis looks slightly weaker versus the prior quarter. "
        "Cited score or MoS moves crossed the softer threshold — dig into the evidence."
    ),
    ThesisVerdict.BROKEN: (
        "Thesis signals crossed a Broken threshold (large score drop, MoS flip, "
        "or net-cash deterioration). Re-read the original thesis against the evidence."
    ),
}


def parse_insight_mode(raw: str | None) -> ThesisInsightMode:
    try:
        return ThesisInsightMode((raw or "deterministic").strip().lower())
    except ValueError:
        return ThesisInsightMode.DETERMINISTIC


def deterministic_narrative(change: ThesisChange) -> str:
    label = THESIS_VERDICT_LABELS.get(change.verdict, change.verdict.value)
    bits = "; ".join(change.evidence[:4]) if change.evidence else "no cited deltas"
    return f"{label}. Evidence: {bits}."


def canned_narrative(change: ThesisChange) -> str:
    base = _CANNED.get(change.verdict, _CANNED[ThesisVerdict.NO_CHANGE])
    if change.evidence:
        return f"{base} Evidence: {'; '.join(change.evidence[:3])}."
    return base


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


def _contains_directive(text: str) -> bool:
    lowered = text.lower()
    return any(n in lowered for n in _DIRECTIVE_NEEDLES)


def llm_narrative(
    change: ThesisChange,
    *,
    ticker: str,
    original_thesis: str,
    app_settings: Settings,
) -> str | None:
    """Gemini narrative; return None on any failure or directive phrasing."""
    api_key = app_settings.google_api_key
    if not api_key:
        logger.info("thesis_llm_skip reason=no_api_key")
        return None
    label = THESIS_VERDICT_LABELS.get(change.verdict, change.verdict.value)
    prompt = (
        "You monitor investment theses, not prices. Return ONLY JSON with key "
        "'narrative' (string, ≤400 chars). Describe what changed vs the prior "
        "quarter using the closed verdict and evidence. "
        "Do NOT give buy/sell/trim/hold/wait advice. "
        f"Ticker={ticker} verdict={label} "
        f"evidence={change.evidence!r} original_thesis={original_thesis[:300]!r}"
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
        if not data or not isinstance(data.get("narrative"), str):
            logger.info("thesis_llm_parse_fail ticker=%s", ticker)
            return None
        narrative = str(data["narrative"]).strip()
        if not narrative or _contains_directive(narrative):
            logger.info("thesis_llm_reject ticker=%s", ticker)
            return None
        return narrative[:500]
    except Exception as exc:  # noqa: BLE001 — fail-closed
        logger.info(
            "thesis_llm_fail ticker=%s err=%s", ticker, exc.__class__.__name__
        )
        return None


def narrate_change(
    change: ThesisChange,
    *,
    ticker: str = "",
    original_thesis: str = "",
    mode: ThesisInsightMode | str | None = None,
    app_settings: Settings | None = None,
) -> ThesisChange:
    """Fill narrative + insight_mode; llm fails closed to deterministic."""
    s = app_settings if app_settings is not None else default_settings
    if mode is None:
        resolved = parse_insight_mode(getattr(s, "thesis_insight_mode", "deterministic"))
    elif isinstance(mode, ThesisInsightMode):
        resolved = mode
    else:
        resolved = parse_insight_mode(str(mode))

    if resolved == ThesisInsightMode.LLM:
        text = llm_narrative(
            change,
            ticker=ticker,
            original_thesis=original_thesis,
            app_settings=s,
        )
        if text:
            return change.model_copy(
                update={
                    "narrative": text,
                    "insight_mode": ThesisInsightMode.LLM.value,
                }
            )
        # fail-closed
        resolved = ThesisInsightMode.DETERMINISTIC

    if resolved == ThesisInsightMode.CANNED:
        return change.model_copy(
            update={
                "narrative": canned_narrative(change),
                "insight_mode": ThesisInsightMode.CANNED.value,
            }
        )

    return change.model_copy(
        update={
            "narrative": deterministic_narrative(change),
            "insight_mode": ThesisInsightMode.DETERMINISTIC.value,
        }
    )

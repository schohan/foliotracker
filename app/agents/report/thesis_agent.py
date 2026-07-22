"""Investment thesis generator — sole LLM step in Phase 0."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from google import genai
from pydantic import ValidationError

from app.configs.settings import settings
from app.schemas.evidence import EvidenceBundle
from app.schemas.phase0 import assert_claims_cite_bundle
from app.schemas.report import InvestmentThesis

logger = logging.getLogger(__name__)


class ThesisGenerationError(RuntimeError):
    """LLM returned empty/unusable thesis output."""


class UncitedClaimError(ValueError):
    """Thesis contains material claims without valid evidence citations."""


class DanglingCitationError(ValueError):
    """Thesis cites evidence ids not present in the bundle."""


_THESIS_SCHEMA_HINT = """
Return ONLY valid JSON matching this shape (no markdown):
{
  "ticker": "STRING",
  "thesis": "short summary string",
  "claims": [
    {"text": "assertion grounded in evidence", "evidence_ids": ["ev_..."]}
  ],
  "bull_case": "string or null",
  "bear_case": "string or null",
  "key_risks": ["string"],
  "conviction": 0.0
}
Rules:
- Every claim MUST include at least one evidence_ids entry from the provided bundle.
- Do NOT invent numeric metrics not present in evidence data.
- If a field is null in evidence, do not claim a value for it.
- Prefer 2-5 claims.
"""


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _validate_thesis(thesis: InvestmentThesis, bundle: EvidenceBundle) -> None:
    if not thesis.claims:
        raise UncitedClaimError("thesis has no claims")
    try:
        assert_claims_cite_bundle(thesis, bundle)
    except ValueError as exc:
        raise DanglingCitationError(str(exc)) from exc


def _build_prompt(bundle: EvidenceBundle, *, repair: bool) -> str:
    payload = bundle.model_dump(mode="json")
    repair_line = ""
    if repair:
        repair_line = (
            "\nPREVIOUS OUTPUT FAILED CITATION CHECK. "
            "Cite evidence ids from the bundle or remove uncited claims. "
            "Do not invent ids.\n"
        )
    return (
        f"You are FolioTracker's thesis agent. Ground every material claim in evidence.\n"
        f"{repair_line}\n"
        f"EvidenceBundle JSON:\n{json.dumps(payload, indent=2)}\n\n"
        f"{_THESIS_SCHEMA_HINT}"
    )


def _interaction_text(interaction: Any) -> str:
    """Extract final text from an Interactions API response."""
    text = getattr(interaction, "output_text", None) or ""
    if text and str(text).strip():
        return str(text)

    # Fallback: walk steps for model_output / text content (SDK schema variants)
    steps = getattr(interaction, "steps", None) or []
    chunks: list[str] = []
    for step in steps:
        step_type = getattr(step, "type", None) or (
            step.get("type") if isinstance(step, dict) else None
        )
        if step_type not in (None, "model_output", "text"):
            # Still try to pull text from any step that has it
            pass
        content = getattr(step, "content", None)
        if content is None and isinstance(step, dict):
            content = step.get("content")
        if isinstance(content, str) and content.strip():
            chunks.append(content)
            continue
        if not content:
            # Some schemas expose .text directly on the step
            direct = getattr(step, "text", None)
            if direct:
                chunks.append(str(direct))
            continue
        for part in content:
            part_text = getattr(part, "text", None)
            if part_text is None and isinstance(part, dict):
                part_text = part.get("text")
            if part_text:
                chunks.append(str(part_text))
    return "".join(chunks)


def _call_model(prompt: str) -> str:
    """Call Gemini via the Interactions API (not legacy generateContent)."""
    if not settings.google_api_key:
        raise ThesisGenerationError("GOOGLE_API_KEY is not set")
    client = genai.Client(api_key=settings.google_api_key)
    interaction = client.interactions.create(
        model=settings.default_model,
        input=prompt,
        response_format=[
            {
                "type": "text",
                "mime_type": "application/json",
                "schema": InvestmentThesis.model_json_schema(),
            }
        ],
    )
    text = _interaction_text(interaction)
    if not text.strip():
        raise ThesisGenerationError("empty model response")
    return text


def generate_thesis(
    bundle: EvidenceBundle,
    *,
    model_caller: Any | None = None,
) -> InvestmentThesis:
    """Generate InvestmentThesis with one citation-repair retry (3A).

    Args:
        bundle: Evidence for the ticker.
        model_caller: Optional callable(prompt) -> str for tests.
    """
    caller = model_caller or _call_model
    last_error: Exception | None = None

    for attempt in (1, 2):
        repair = attempt == 2
        prompt = _build_prompt(bundle, repair=repair)
        try:
            raw = caller(prompt)
            data = _extract_json(raw)
            thesis = InvestmentThesis.model_validate(data)
            if thesis.ticker.upper() != bundle.ticker.upper():
                thesis = thesis.model_copy(update={"ticker": bundle.ticker})
            _validate_thesis(thesis, bundle)
            logger.info(
                "thesis_ok ticker=%s attempt=%s claims=%s",
                bundle.ticker,
                attempt,
                len(thesis.claims),
            )
            return thesis
        except (
            json.JSONDecodeError,
            ValidationError,
            UncitedClaimError,
            DanglingCitationError,
            ThesisGenerationError,
        ) as exc:
            last_error = exc
            logger.warning(
                "thesis_attempt_failed ticker=%s attempt=%s err=%s",
                bundle.ticker,
                attempt,
                exc,
            )
            continue

    assert last_error is not None
    if isinstance(last_error, (UncitedClaimError, DanglingCitationError)):
        raise last_error
    raise ThesisGenerationError(str(last_error)) from last_error


# Convenience for ADK-style export (optional agent wrapper later)
def run(bundle: EvidenceBundle, **kwargs: Any) -> InvestmentThesis:
    return generate_thesis(bundle, **kwargs)

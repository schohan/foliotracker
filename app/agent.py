"""Portfolio / stock research orchestrator agent (ADK entrypoint)."""

from __future__ import annotations

import logging

from google.adk.agents import Agent

from app.configs.settings import settings
from app.services.phase0_pipeline import run_phase0_research

logger = logging.getLogger(__name__)


def analyze_ticker(ticker: str) -> dict:
    """Run research for a stock ticker and return the full Phase0Result JSON.

    Fetches Yahoo Finance metrics (enriched fundamentals) and Google News /
    SEC in parallel, merges cited evidence (with conflict records when sources
    disagree), generates an investment thesis that must cite evidence ids, and
    uses local TTL caches (whole-result + per-source).

    Args:
        ticker: Equity symbol, e.g. NVDA or AAPL.

    Returns:
        Full Phase0Result as a JSON-serializable dict. Always includes
        disclaimer, cache_hit, and request_id. On success/partial also includes
        fundamentals (enriched metrics), evidence (with conflicts), scorecard,
        and thesis when available.
    """
    result = run_phase0_research(ticker)
    payload = result.model_dump(mode="json")
    logger.info(
        "analyze_ticker done ticker=%s status=%s cache_hit=%s request_id=%s "
        "has_fundamentals=%s",
        payload.get("ticker"),
        payload.get("status"),
        payload.get("cache_hit"),
        payload.get("request_id"),
        payload.get("fundamentals") is not None,
    )
    return payload


root_agent = Agent(
    name="portfolio_research_agent",
    model=settings.default_model,
    description=(
        "Portfolio Research Agent — Yahoo fundamentals + Google News + SEC → "
        "merged evidence (with conflicts) → cited investment thesis. "
        "Always returns the full Phase0Result JSON for debugging."
    ),
    instruction=(
        "You are the FolioTracker Portfolio Research Agent.\n"
        "When the user asks to research or analyze a stock, extract the ticker "
        "and call analyze_ticker.\n"
        "\n"
        "DEBUGGING / OUTPUT FORMAT (required):\n"
        "1) FIRST output the COMPLETE analyze_ticker return value as a single "
        "fenced JSON code block (pretty-printed). Do not omit fields. Include "
        "fundamentals, evidence (all items + conflicts), scorecard, thesis, "
        "status, disclaimer, cache_hit, and request_id.\n"
        "2) AFTER the JSON, you may add a short human summary (scorecard, "
        "thesis highlights, conflicts). The JSON is the source of truth — "
        "never invent metrics that are missing from it.\n"
        "\n"
        "If status is error: still show the full JSON when present, then explain "
        "error_message in plain language (do not dump exception class names). "
        "State whether evidence/fundamentals are still present. If error_code "
        "starts with THESIS_, clarify that market/news evidence may have been "
        "gathered but a cited thesis could not be shipped. Always include "
        "request_id for support.\n"
        "If evidence.conflicts is non-empty, call out each conflict explicitly "
        "instead of averaging sources into false consensus.\n"
        "If the user does not provide a ticker, ask for one.\n"
        "Do not invent financial metrics yourself — only use analyze_ticker.\n"
        "Remind users the output is not investment advice when presenting results."
    ),
    tools=[analyze_ticker],
)

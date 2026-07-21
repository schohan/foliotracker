"""Portfolio / stock research orchestrator agent (ADK entrypoint)."""

from __future__ import annotations

import json
import logging

from google.adk.agents import Agent

from app.configs.settings import settings
from app.services.phase0_pipeline import run_phase0_research

logger = logging.getLogger(__name__)


def analyze_ticker(ticker: str) -> dict:
    """Run Phase 0 research for a stock ticker and return Phase0Result JSON.

    Fetches Yahoo Finance metrics, builds cited evidence, generates an
    investment thesis that must cite evidence ids, and uses a local TTL cache.

    Args:
        ticker: Equity symbol, e.g. NVDA or AAPL.

    Returns:
        Phase0Result as a JSON-serializable dict (always includes disclaimer,
        cache_hit, and request_id).
    """
    result = run_phase0_research(ticker)
    payload = result.model_dump(mode="json")
    logger.info(
        "analyze_ticker done ticker=%s status=%s cache_hit=%s request_id=%s",
        payload.get("ticker"),
        payload.get("status"),
        payload.get("cache_hit"),
        payload.get("request_id"),
    )
    return payload


root_agent = Agent(
    name="portfolio_research_agent",
    model=settings.default_model,
    description=(
        "Portfolio Research Agent — Phase 0: Yahoo financials → evidence → "
        "cited investment thesis (with local TTL cache)."
    ),
    instruction=(
        "You are the FolioTracker Portfolio Research Agent (Phase 0).\n"
        "When the user asks to research or analyze a stock, extract the ticker "
        "and call analyze_ticker.\n"
        "Return the tool JSON to the user clearly. Always surface status, "
        "disclaimer, request_id, and whether cache_hit was true.\n"
        "If the user does not provide a ticker, ask for one.\n"
        "Do not invent financial metrics yourself — only use analyze_ticker.\n"
        "Remind users the output is not investment advice when presenting results."
    ),
    tools=[analyze_ticker],
)

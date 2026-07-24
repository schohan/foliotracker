"""5A session clear between research requests."""

from __future__ import annotations

from app.services.phase0_session import clear_research_session, new_research_session


def test_session_clear_drops_prior_ticker_state() -> None:
    state = {
        "ticker": "NVDA",
        "financial_metrics": {"pe_ratio": 30},
        "news_batch": {"ticker": "NVDA"},
        "filings_batch": {"ticker": "NVDA"},
        "evidence_bundle": {"ticker": "NVDA"},
        "scorecard": {"ticker": "NVDA"},
        "thesis": {"ticker": "NVDA"},
        "phase0_status": "ok",
        "cache_hit": False,
    }
    cleared = clear_research_session(state)
    assert cleared.get("financial_metrics") is None
    assert cleared.get("news_batch") is None
    assert cleared.get("filings_batch") is None
    assert cleared.get("evidence_bundle") is None
    assert cleared.get("scorecard") is None
    assert cleared.get("thesis") is None
    assert cleared.get("phase0_status") is None

    started = new_research_session(cleared, "AAPL")
    assert started["ticker"] == "AAPL"

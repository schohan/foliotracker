"""Root agent must surface full Phase0Result JSON for debugging."""

from __future__ import annotations

from app.agent import analyze_ticker, root_agent


def test_root_agent_instruction_requires_full_json() -> None:
    text = root_agent.instruction
    assert "COMPLETE" in text or "complete" in text.lower()
    assert "fundamentals" in text
    assert "JSON" in text
    assert "analyze_ticker" in text


def test_analyze_ticker_is_callable_tool() -> None:
    assert callable(analyze_ticker)
    assert analyze_ticker.__name__ == "analyze_ticker"

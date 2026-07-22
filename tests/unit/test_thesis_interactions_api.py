"""Thesis agent uses Gemini Interactions API (not generateContent)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.agents.report import thesis_agent
from app.agents.report.thesis_agent import ThesisGenerationError, _call_model


def test_call_model_uses_interactions_create(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.configs.settings import Settings

    monkeypatch.setattr(
        thesis_agent,
        "settings",
        Settings(google_api_key="test-key", default_model="gemini-2.0-flash"),
    )

    created: dict = {}

    class FakeInteractions:
        def create(self, **kwargs):
            created.update(kwargs)
            return SimpleNamespace(output_text='{"ticker":"NVDA","thesis":"ok","claims":[]}')

    class FakeClient:
        def __init__(self, *a, **k):
            self.interactions = FakeInteractions()

    monkeypatch.setattr(thesis_agent.genai, "Client", FakeClient)

    text = _call_model("hello")
    assert "NVDA" in text
    assert created["input"] == "hello"
    assert created["model"] == "gemini-2.0-flash"
    assert isinstance(created.get("response_format"), list)
    assert created["response_format"][0]["mime_type"] == "application/json"


def test_call_model_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.configs.settings import Settings

    monkeypatch.setattr(
        thesis_agent,
        "settings",
        Settings(google_api_key=None),
    )
    with pytest.raises(ThesisGenerationError, match="GOOGLE_API_KEY"):
        _call_model("hello")


def test_call_model_falls_back_to_steps(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.configs.settings import Settings

    monkeypatch.setattr(
        thesis_agent,
        "settings",
        Settings(google_api_key="test-key", default_model="gemini-2.0-flash"),
    )

    class FakeInteractions:
        def create(self, **kwargs):
            return SimpleNamespace(
                output_text="",
                steps=[
                    SimpleNamespace(
                        type="model_output",
                        content=[SimpleNamespace(text='{"ok": true}')],
                    )
                ],
            )

    class FakeClient:
        def __init__(self, *a, **k):
            self.interactions = FakeInteractions()

    monkeypatch.setattr(thesis_agent.genai, "Client", FakeClient)
    assert _call_model("x") == '{"ok": true}'

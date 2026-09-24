# tests/test_agents_triage.py
# Purpose: Unit tests for the Triage Agent (app.agents.triage). Mocks the LLM client layer so no
#          real API call is made: happy-path structured output, and malformed-output handling
#          (falls back to prompted JSON, then returns a typed AgentError rather than crashing).
# Author: CloudDesk Team
# Date: 2026-09-24

import pytest

from app.agents.schemas import TriageResult
from app.agents.triage import run_triage_agent
from app.llm.structured import AgentError
from tests._llm_fakes import FakeCompletion, FakeLLM, FakeMessage


async def test_triage_agent_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """A well-formed native structured-output response is returned as a TriageResult."""
    fake_llm = FakeLLM()
    expected = TriageResult(
        intents=["billing", "technical"],
        priority="high",
        sentiment="frustrated",
        required_agents=["billing", "technical"],
        reason="Duplicate charge and API access issue after upgrade.",
    )
    fake_llm.client.beta.chat.completions.parse.return_value = FakeCompletion(
        FakeMessage(parsed=expected)
    )
    monkeypatch.setattr("app.llm.structured.get_llm_client", lambda: fake_llm)

    result = await run_triage_agent("I was charged twice and my API stopped working.")

    assert isinstance(result, TriageResult)
    assert result.priority == "high"
    assert "billing" in result.required_agents
    fake_llm.client.beta.chat.completions.parse.assert_awaited_once()


async def test_triage_agent_handles_malformed_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """Native mode failing, then non-JSON fallback content, yields AgentError (never a crash)."""
    fake_llm = FakeLLM()
    fake_llm.client.beta.chat.completions.parse.side_effect = Exception("model rejects schema")
    fake_llm.client.chat.completions.create.return_value = FakeCompletion(
        FakeMessage(content="not valid json at all")
    )
    monkeypatch.setattr("app.llm.structured.get_llm_client", lambda: fake_llm)

    result = await run_triage_agent("Some ambiguous message")

    assert isinstance(result, AgentError)
    assert result.agent == "triage"
    # one native attempt + (1 initial + MAX_JSON_RETRIES) fallback attempts
    assert fake_llm.client.chat.completions.create.await_count == 2


async def test_triage_agent_has_no_tools() -> None:
    """Spec section 9: the Triage Agent must never be given tools."""
    import app.agents.triage as triage_module

    assert not hasattr(triage_module, "_build_tools")

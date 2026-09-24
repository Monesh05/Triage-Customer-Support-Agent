# tests/test_agents_resolution.py
# Purpose: Unit tests for the Resolution Agent (app.agents.resolution). Mocks the LLM client
#          layer. Covers the happy path (synthesizing specialist findings into a structured
#          resolution) and malformed-output handling.
# Author: CloudDesk Team
# Date: 2026-09-24

import pytest

from app.agents.resolution import run_resolution_agent
from app.agents.schemas import ResolutionAgentResult
from app.llm.structured import AgentError
from tests._llm_fakes import FakeCompletion, FakeLLM, FakeMessage


async def test_resolution_agent_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Specialist findings are synthesized into a structured ResolutionAgentResult."""
    fake_llm = FakeLLM()
    expected = ResolutionAgentResult(
        summary="Duplicate billing and a stale API entitlement were both confirmed.",
        issues_identified=["Duplicate payment of $49.", "API entitlement not synced with Pro."],
        proposed_resolution="Create a refund request and refresh the entitlement.",
        customer_facing_draft="We found two issues and are working on both...",
        unresolved_questions=[],
        requires_approval=True,
    )
    fake_llm.client.beta.chat.completions.parse.return_value = FakeCompletion(
        FakeMessage(parsed=expected)
    )
    monkeypatch.setattr("app.llm.structured.get_llm_client", lambda: fake_llm)

    specialist_results = {
        "billing": {"status": "resolved", "findings": [{"fact": "Duplicate payment confirmed."}]},
        "technical": {"hypothesis": "API 403 caused by stale entitlement.", "status": "resolved"},
    }
    result = await run_resolution_agent("I was charged twice and my API is broken.", specialist_results)

    assert isinstance(result, ResolutionAgentResult)
    assert result.requires_approval is True


async def test_resolution_agent_handles_malformed_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """A model reply that never yields valid JSON returns AgentError, not a crash."""
    fake_llm = FakeLLM()
    fake_llm.client.beta.chat.completions.parse.side_effect = Exception("no schema support")
    fake_llm.client.chat.completions.create.return_value = FakeCompletion(
        FakeMessage(content="not json")
    )
    monkeypatch.setattr("app.llm.structured.get_llm_client", lambda: fake_llm)

    result = await run_resolution_agent("test", {"billing": {"status": "unresolved"}})

    assert isinstance(result, AgentError)
    assert result.agent == "resolution"

# tests/test_agents_technical.py
# Purpose: Unit tests for the Technical Support Agent (app.agents.technical). Mocks the LLM
#          client layer AND the underlying Phase 2 technical/product tool functions. Covers the
#          happy path, malformed-output handling, the exact allowed-tool set (spec section 12),
#          and that the bounded tool-call loop respects MAX_TOOL_CALL_ROUNDS.
# Author: CloudDesk Team
# Date: 2026-09-24

import json
from unittest.mock import AsyncMock

import pytest

from app.agents.base import MAX_TOOL_CALL_ROUNDS
from app.agents.schemas import TechnicalAgentResult
from app.agents.technical import _build_tools, run_technical_agent
from app.llm.structured import AgentError
from app.tools.base import ToolResult
from tests._llm_fakes import FakeCompletion, FakeLLM, FakeMessage, FakeToolCall


def test_technical_agent_tool_allowlist() -> None:
    """Spec section 12: the Technical Agent may only call these exact six tools."""
    names = {spec.name for spec in _build_tools()}
    assert names == {
        "get_api_usage",
        "get_api_key_status",
        "get_service_status",
        "search_error_logs",
        "get_recent_incidents",
        "search_product_docs",
    }


async def test_technical_agent_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """The agent calls an allowed tool, then produces a structured TechnicalAgentResult."""
    fake_llm = FakeLLM()
    tool_call = FakeToolCall("call_1", "get_recent_incidents", "{}")
    fake_llm.client.chat.completions.create.side_effect = [
        FakeCompletion(FakeMessage(tool_calls=[tool_call])),
        FakeCompletion(FakeMessage(content=None, tool_calls=None)),
    ]
    expected = TechnicalAgentResult(
        hypothesis="API 403 caused by stale subscription entitlement.",
        status="resolved",
        evidence=["No active API outage.", "API key is active."],
        recommended_actions=[],
    )
    fake_llm.client.beta.chat.completions.parse.return_value = FakeCompletion(
        FakeMessage(parsed=expected)
    )
    monkeypatch.setattr("app.agents.base.get_llm_client", lambda: fake_llm)
    monkeypatch.setattr("app.llm.structured.get_llm_client", lambda: fake_llm)
    fake_incidents = AsyncMock(return_value=ToolResult(success=True, data=[]))
    monkeypatch.setattr("app.agents.technical.technical_tools.get_recent_incidents", fake_incidents)

    result = await run_technical_agent("cust-1", "My API returns 403.")

    assert isinstance(result, TechnicalAgentResult)
    assert "stale" in result.hypothesis
    fake_incidents.assert_awaited_once_with()


async def test_technical_agent_handles_malformed_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """A model reply that never yields valid JSON returns AgentError, not a crash."""
    fake_llm = FakeLLM()
    fake_llm.client.chat.completions.create.side_effect = [
        FakeCompletion(FakeMessage(content=None, tool_calls=None)),
        FakeCompletion(FakeMessage(content="nope")),
        FakeCompletion(FakeMessage(content="still nope")),
    ]
    fake_llm.client.beta.chat.completions.parse.side_effect = Exception("no schema support")
    monkeypatch.setattr("app.agents.base.get_llm_client", lambda: fake_llm)
    monkeypatch.setattr("app.llm.structured.get_llm_client", lambda: fake_llm)

    result = await run_technical_agent("cust-1", "API is down.")

    assert isinstance(result, AgentError)
    assert result.agent == "technical"


async def test_technical_agent_tool_loop_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    """If the model keeps requesting tools forever, the loop stops after MAX_TOOL_CALL_ROUNDS."""
    fake_llm = FakeLLM()

    def _always_call_tool(*_args: object, **_kwargs: object) -> FakeCompletion:
        call = FakeToolCall("call_x", "get_recent_incidents", "{}")
        return FakeCompletion(FakeMessage(tool_calls=[call]))

    fake_llm.client.chat.completions.create.side_effect = _always_call_tool
    fake_llm.client.beta.chat.completions.parse.return_value = FakeCompletion(
        FakeMessage(
            parsed=TechnicalAgentResult(
                hypothesis="unclear", status="unresolved", evidence=[], recommended_actions=[]
            )
        )
    )
    monkeypatch.setattr("app.agents.base.get_llm_client", lambda: fake_llm)
    monkeypatch.setattr("app.llm.structured.get_llm_client", lambda: fake_llm)
    monkeypatch.setattr(
        "app.agents.technical.technical_tools.get_recent_incidents",
        AsyncMock(return_value=ToolResult(success=True, data=[])),
    )

    result = await run_technical_agent("cust-1", "loop forever please")

    assert isinstance(result, TechnicalAgentResult)
    assert fake_llm.client.chat.completions.create.await_count == MAX_TOOL_CALL_ROUNDS

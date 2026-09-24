# tests/test_agents_account.py
# Purpose: Unit tests for the Account Agent (app.agents.account). Mocks the LLM client layer AND
#          the underlying Phase 2 account tool functions. Covers the happy path, malformed-output
#          handling, and the exact allowed-tool set (spec section 11).
# Author: CloudDesk Team
# Date: 2026-09-24

import json
from unittest.mock import AsyncMock

import pytest

from app.agents.account import _build_tools, run_account_agent
from app.agents.schemas import AccountAgentResult, Finding, RecommendedAction
from app.llm.structured import AgentError
from app.tools.base import ToolResult
from tests._llm_fakes import FakeCompletion, FakeLLM, FakeMessage, FakeToolCall


def test_account_agent_tool_allowlist() -> None:
    """Spec section 11: the Account Agent may only call these exact five tools."""
    names = {spec.name for spec in _build_tools()}
    assert names == {
        "get_account",
        "get_login_history",
        "get_account_permissions",
        "get_subscription_entitlements",
        "check_mfa_status",
    }


async def test_account_agent_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """The agent calls an allowed tool, then produces a structured AccountAgentResult."""
    fake_llm = FakeLLM()
    tool_call = FakeToolCall(
        "call_1", "get_subscription_entitlements", json.dumps({"customer_id": "cust-1"})
    )
    fake_llm.client.chat.completions.create.side_effect = [
        FakeCompletion(FakeMessage(tool_calls=[tool_call])),
        FakeCompletion(FakeMessage(content=None, tool_calls=None)),
    ]
    expected = AccountAgentResult(
        status="resolved",
        findings=[Finding(fact="Subscription is Pro but granted entitlement is Free.")],
        recommended_actions=[RecommendedAction(action="refresh_entitlement", requires_approval=True)],
        evidence=["subscription=PRO", "entitlement=FREE"],
    )
    fake_llm.client.beta.chat.completions.parse.return_value = FakeCompletion(
        FakeMessage(parsed=expected)
    )
    monkeypatch.setattr("app.agents.base.get_llm_client", lambda: fake_llm)
    monkeypatch.setattr("app.llm.structured.get_llm_client", lambda: fake_llm)
    fake_entitlements = AsyncMock(return_value=ToolResult(success=True, data=[]))
    monkeypatch.setattr(
        "app.agents.account.account_tools.get_subscription_entitlements", fake_entitlements
    )

    result = await run_account_agent("cust-1", "I can't access the Pro API.")

    assert isinstance(result, AccountAgentResult)
    assert "entitlement=FREE" in result.evidence
    fake_entitlements.assert_awaited_once_with("cust-1")


async def test_account_agent_handles_malformed_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """A model reply that never yields valid JSON returns AgentError, not a crash."""
    fake_llm = FakeLLM()
    fake_llm.client.chat.completions.create.side_effect = [
        FakeCompletion(FakeMessage(content=None, tool_calls=None)),
        FakeCompletion(FakeMessage(content="{broken")),
        FakeCompletion(FakeMessage(content="{still broken")),
    ]
    fake_llm.client.beta.chat.completions.parse.side_effect = Exception("no schema support")
    monkeypatch.setattr("app.agents.base.get_llm_client", lambda: fake_llm)
    monkeypatch.setattr("app.llm.structured.get_llm_client", lambda: fake_llm)

    result = await run_account_agent("cust-1", "I can't log in.")

    assert isinstance(result, AgentError)
    assert result.agent == "account"

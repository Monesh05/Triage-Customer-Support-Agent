# tests/test_agents_product.py
# Purpose: Unit tests for the Product Agent (app.agents.product). Mocks the LLM client layer AND
#          the underlying search_product_docs tool (Phase 6: real pgvector retrieval, mocked
#          here at the tool boundary). Covers the happy (grounded) path with rich source
#          metadata, the ungrounded "no matches" path, malformed-output handling, and the exact
#          single-tool allowlist (spec section 13).
# Author: CloudDesk Team
# Date: 2026-09-24

import json
from unittest.mock import AsyncMock

import pytest

from app.agents.product import _build_tools, run_product_agent
from app.agents.schemas import ProductAgentResult, ProductSource
from app.llm.structured import AgentError
from app.tools.base import ToolResult
from tests._llm_fakes import FakeCompletion, FakeLLM, FakeMessage, FakeToolCall


def test_product_agent_tool_allowlist() -> None:
    """Spec section 13: the Product Agent may only call search_product_docs."""
    names = {spec.name for spec in _build_tools()}
    assert names == {"search_product_docs"}


async def test_product_agent_happy_path_grounded(monkeypatch: pytest.MonkeyPatch) -> None:
    """A found doc match is cited in `sources` and `grounded` is true."""
    fake_llm = FakeLLM()
    tool_call = FakeToolCall("call_1", "search_product_docs", json.dumps({"query": "MFA"}))
    fake_llm.client.chat.completions.create.side_effect = [
        FakeCompletion(FakeMessage(tool_calls=[tool_call])),
        FakeCompletion(FakeMessage(content=None, tool_calls=None)),
    ]
    expected = ProductAgentResult(
        answer="MFA can be enabled from account security settings.",
        sources=[
            ProductSource(document_id="mfa-setup", title="How MFA Works", category="feature documentation")
        ],
        grounded=True,
    )
    fake_llm.client.beta.chat.completions.parse.return_value = FakeCompletion(
        FakeMessage(parsed=expected)
    )
    monkeypatch.setattr("app.agents.base.get_llm_client", lambda: fake_llm)
    monkeypatch.setattr("app.llm.structured.get_llm_client", lambda: fake_llm)
    fake_search = AsyncMock(return_value=ToolResult(success=True, data=None))
    monkeypatch.setattr("app.agents.product.product_tools.search_product_docs", fake_search)

    result = await run_product_agent("How does MFA work?")

    assert isinstance(result, ProductAgentResult)
    assert result.grounded is True
    assert result.sources[0].document_id == "mfa-setup"
    assert result.sources[0].category == "feature documentation"
    fake_search.assert_awaited_once_with("MFA", category=None, product=None)


async def test_product_agent_handles_malformed_output(monkeypatch: pytest.MonkeyPatch) -> None:
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

    result = await run_product_agent("Does Pro support 100k requests?")

    assert isinstance(result, AgentError)
    assert result.agent == "product"

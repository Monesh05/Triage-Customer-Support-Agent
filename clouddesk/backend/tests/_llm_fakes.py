# tests/_llm_fakes.py
# Purpose: Fake OpenAI SDK response objects used by tests/test_agents_*.py to mock the LLM
#          client layer (app.llm.client.get_llm_client) so the agent test suite never makes a
#          real network/API call. Not a test module itself (no test_ prefix) — pytest does not
#          collect it directly.
# Author: CloudDesk Team
# Date: 2026-09-24

from typing import Any
from unittest.mock import AsyncMock, MagicMock


class FakeToolCallFunction:
    """Mirrors openai.types.chat.ChatCompletionMessageToolCall.function."""

    def __init__(self, name: str, arguments: str) -> None:
        self.name = name
        self.arguments = arguments


class FakeToolCall:
    """Mirrors openai.types.chat.ChatCompletionMessageToolCall closely enough for the tool loop."""

    def __init__(self, call_id: str, name: str, arguments: str) -> None:
        self.id = call_id
        self.type = "function"
        self.function = FakeToolCallFunction(name, arguments)

    def model_dump(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "function": {"name": self.function.name, "arguments": self.function.arguments},
        }


class FakeMessage:
    """Mirrors openai.types.chat.ChatCompletionMessage (only the fields agents read)."""

    def __init__(
        self,
        content: str | None = None,
        tool_calls: list[FakeToolCall] | None = None,
        parsed: Any | None = None,
    ) -> None:
        self.content = content
        self.tool_calls = tool_calls
        self.parsed = parsed


class FakeCompletion:
    """Mirrors the top level of a ChatCompletion/ParsedChatCompletion response."""

    def __init__(self, message: FakeMessage) -> None:
        self.choices = [MagicMock(message=message)]


class FakeLLM:
    """Duck-typed stand-in for app.llm.client.LLMClient with AsyncMock-backed SDK calls."""

    def __init__(self, model: str = "fake-model", provider: str = "openai") -> None:
        self.model = model
        self.provider = provider
        self.client = MagicMock()
        self.client.beta = MagicMock()
        self.client.beta.chat = MagicMock()
        self.client.beta.chat.completions = MagicMock()
        self.client.beta.chat.completions.parse = AsyncMock()
        self.client.chat = MagicMock()
        self.client.chat.completions = MagicMock()
        self.client.chat.completions.create = AsyncMock()

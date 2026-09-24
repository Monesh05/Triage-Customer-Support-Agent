# app/agents/base.py
# Purpose: Shared building blocks for the Phase 3 agent layer: the typed AgentError result
#          (re-exported from app.llm.structured), the ToolSpec wrapper that exposes an allowed
#          Phase 2 tool function to the LLM as an OpenAI function-calling tool, and the bounded
#          tool-use loop shared by the Billing/Account/Technical/Product specialist agents
#          (spec section 10-13: agents may only call the tools explicitly listed for them).
# Author: CloudDesk Team
# Date: 2026-09-24

import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

from openai.types.chat import ChatCompletionMessageParam
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall
from pydantic import BaseModel

from app.llm.client import get_llm_client
from app.llm.structured import AgentError, get_structured_completion
from app.observability.tracer import record_tool_call
from app.tools.base import ToolResult

logger = logging.getLogger("clouddesk.agents")

MAX_TOOL_CALL_ROUNDS: int = 5
FINAL_SYNTHESIS_INSTRUCTION: str = (
    "You have gathered the tool evidence above (or none was needed/available). Do not call "
    "any more tools. Produce the final structured result now, using ONLY the tool results "
    "shown in this conversation as evidence. Never state that an action succeeded unless its "
    "tool result shows success=true."
)

SchemaT = TypeVar("SchemaT", bound=BaseModel)

__all__ = ["AgentError", "ToolSpec", "run_tool_using_agent", "MAX_TOOL_CALL_ROUNDS"]


@dataclass(frozen=True)
class ToolSpec:
    """Wraps one allowed Phase 2 tool function as an OpenAI function-calling tool.

    `handler` should be a thin async wrapper that exposes only the parameters the LLM is
    allowed to set (e.g. never an `actor` override) and returns the tool's real ToolResult.
    """

    name: str
    description: str
    parameters: dict[str, object]
    handler: Callable[..., Awaitable[ToolResult[object]]]

    def to_openai_tool(self) -> dict[str, object]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


async def _execute_tool_call(
    tool_call: ChatCompletionMessageToolCall, tools_by_name: dict[str, ToolSpec]
) -> str:
    """Run one model-requested tool call against its real, allow-listed Phase 2 handler.

    Also reports the call (redacted/truncated, per app.observability.tracer) to whichever
    `trace_agent_run` block is currently active, if any — a no-op when called outside one (e.g.
    every agent unit test that calls `run_billing_agent` etc. directly).
    """
    spec = tools_by_name.get(tool_call.function.name)
    if spec is None:
        result_json = json.dumps({"success": False, "error": f"Unknown tool: {tool_call.function.name}"})
        record_tool_call(tool_call.function.name, {}, result_json)
        return result_json
    args: dict[str, object] = {}
    try:
        args = json.loads(tool_call.function.arguments or "{}")
        result = await spec.handler(**args)
        result_json = result.model_dump_json()
    except Exception as exc:  # noqa: BLE001 - last-resort guard; handlers already wrap errors
        result_json = json.dumps({"success": False, "error": f"Tool execution failed: {exc}"})
    record_tool_call(tool_call.function.name, args, result_json)
    return result_json


def _assistant_message_dict(message: object) -> ChatCompletionMessageParam:
    """Build a minimal assistant message dict from an SDK response message (for re-sending)."""
    tool_calls = getattr(message, "tool_calls", None)
    entry: dict[str, object] = {"role": "assistant", "content": getattr(message, "content", None)}
    if tool_calls:
        entry["tool_calls"] = [tc.model_dump() for tc in tool_calls]
    return entry  # type: ignore[return-value]


async def run_tool_using_agent(
    *,
    agent_name: str,
    system_prompt: str,
    user_content: str,
    tools: list[ToolSpec],
    response_model: type[SchemaT],
) -> SchemaT | AgentError:
    """Run a bounded tool-call loop, then produce a final structured result.

    The model may call any of `tools` for up to MAX_TOOL_CALL_ROUNDS rounds. Once it stops
    requesting tools (or the round budget is exhausted), a final structured-output call
    synthesizes `response_model` from the accumulated tool evidence only.
    """
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
    try:
        messages = await _run_rounds(agent_name, messages, tools)
    except Exception as exc:  # noqa: BLE001
        logger.debug("tool_loop_failed agent=%s error=%s", agent_name, exc)
        return AgentError(agent=agent_name, message=f"Tool loop failed: {exc}")
    messages.append({"role": "system", "content": FINAL_SYNTHESIS_INSTRUCTION})
    return await get_structured_completion(
        agent_name=agent_name, messages=messages, response_model=response_model
    )


async def _run_rounds(
    agent_name: str, messages: list[ChatCompletionMessageParam], tools: list[ToolSpec]
) -> list[ChatCompletionMessageParam]:
    """Execute up to MAX_TOOL_CALL_ROUNDS of model-requested tool calls, mutating `messages`."""
    tools_by_name = {spec.name: spec for spec in tools}
    llm = get_llm_client()
    openai_tools = [spec.to_openai_tool() for spec in tools]
    for round_number in range(MAX_TOOL_CALL_ROUNDS):
        completion = await llm.client.chat.completions.create(
            model=llm.model, messages=messages, tools=openai_tools, tool_choice="auto"
        )
        message = completion.choices[0].message
        messages.append(_assistant_message_dict(message))
        if not message.tool_calls:
            break
        logger.debug(
            "tool_round agent=%s round=%d calls=%d",
            agent_name,
            round_number,
            len(message.tool_calls),
        )
        for tool_call in message.tool_calls:
            result_json = await _execute_tool_call(tool_call, tools_by_name)
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result_json})
    return messages

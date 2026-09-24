# app/llm/structured.py
# Purpose: Structured-output helper (spec section 9-17: every agent returns Pydantic output).
#          Prefers the OpenAI SDK's native JSON-schema parsing (`beta.chat.completions.parse`);
#          falls back to prompted JSON + manual `model_validate_json` (retried once) for
#          providers/models that reject strict schema mode (e.g. some OpenRouter models).
#          Never lets a ValidationError/JSONDecodeError/API error propagate to the caller —
#          returns a typed AgentError instead.
# Author: CloudDesk Team
# Date: 2026-09-24

import json
import logging
from typing import TypeVar

from openai import APIError
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, ValidationError

from app.llm.client import LLMClient, get_llm_client

logger = logging.getLogger("clouddesk.llm")

SchemaT = TypeVar("SchemaT", bound=BaseModel)

MAX_JSON_RETRIES: int = 1
STRUCTURED_TEMPERATURE: float = 0.2
JSON_CODE_FENCE: str = "```"


class AgentError(BaseModel):
    """Typed failure result returned instead of letting a raw exception/parse error propagate."""

    agent: str
    message: str


async def get_structured_completion(
    *,
    agent_name: str,
    messages: list[ChatCompletionMessageParam],
    response_model: type[SchemaT],
) -> SchemaT | AgentError:
    """Call the LLM and parse its reply into `response_model`.

    Tries native structured-output parsing first; falls back to prompted JSON + manual
    validation (retried once) if the provider/model does not support strict schema mode.
    """
    llm = get_llm_client()
    try:
        return await _parse_native(llm, messages, response_model)
    except Exception as exc:  # noqa: BLE001 - any native-mode failure falls back to prompted JSON
        logger.debug("native_structured_output_failed agent=%s error=%s", agent_name, exc)
        return await _parse_with_retry(llm, messages, response_model, agent_name)


async def _parse_native(
    llm: LLMClient, messages: list[ChatCompletionMessageParam], response_model: type[SchemaT]
) -> SchemaT:
    """Use the SDK's native structured-output mode. Raises on any failure (caller falls back)."""
    completion = await llm.client.beta.chat.completions.parse(
        model=llm.model,
        messages=messages,
        response_format=response_model,
        temperature=STRUCTURED_TEMPERATURE,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise ValueError("Model returned no parsed structured output")
    return parsed


async def _parse_with_retry(
    llm: LLMClient,
    messages: list[ChatCompletionMessageParam],
    response_model: type[SchemaT],
    agent_name: str,
) -> SchemaT | AgentError:
    """Prompt for raw JSON and validate it manually, retrying once on failure."""
    schema_hint = (
        "Respond with ONLY valid JSON matching this schema, no markdown fences, "
        f"no extra commentary: {response_model.model_json_schema()}"
    )
    attempt_messages: list[ChatCompletionMessageParam] = [
        *messages,
        {"role": "system", "content": schema_hint},
    ]
    last_error = "unknown error"
    for attempt in range(MAX_JSON_RETRIES + 1):
        try:
            content = await _fetch_raw_content(llm, attempt_messages)
            return response_model.model_validate_json(_strip_code_fences(content))
        except (ValidationError, json.JSONDecodeError, APIError, ValueError) as exc:
            last_error = str(exc)
            logger.debug(
                "structured_json_parse_failed agent=%s attempt=%d error=%s",
                agent_name,
                attempt,
                exc,
            )
    return AgentError(agent=agent_name, message=f"Failed to obtain structured output: {last_error}")


async def _fetch_raw_content(llm: LLMClient, messages: list[ChatCompletionMessageParam]) -> str:
    """Fetch a plain (non-structured) completion's text content."""
    completion = await llm.client.chat.completions.create(
        model=llm.model, messages=messages, temperature=STRUCTURED_TEMPERATURE
    )
    content = completion.choices[0].message.content
    if not content:
        raise ValueError("Model returned empty content")
    return content


def _strip_code_fences(content: str) -> str:
    """Strip a leading/trailing ```json ... ``` fence if the model added one anyway."""
    text = content.strip()
    if not text.startswith(JSON_CODE_FENCE):
        return text
    parts = text.split(JSON_CODE_FENCE)
    inner = parts[1] if len(parts) > 1 else text
    if inner.startswith("json"):
        inner = inner[len("json") :]
    return inner.strip()

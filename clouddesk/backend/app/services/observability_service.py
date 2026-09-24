# app/services/observability_service.py
# Purpose: Persistence half of Phase 7 (Agent Observability, spec section 24): redaction and
#          truncation policy for everything written into `agent_runs`, plus the CRUD/query
#          functions the tracer (app.observability.tracer) and the read API
#          (app.api.v1.traces) use. Kept separate from the audit log
#          (app.services.audit_service) on purpose — audit = compliance trail of sensitive
#          business actions; this module = engineering trace of the agent system itself.
#
#          Redaction/truncation policy (documented per this phase's brief):
#          - Any mapping key that matches `SENSITIVE_KEY_SUBSTRINGS` (password/secret/token/
#            authorization/api key/private key/card number/cvv/ssn) has its VALUE replaced with
#            `REDACTED_PLACEHOLDER`, recursively, in both `tool_calls` and `tool_results`.
#          - Free text (`input_summary` source text, `output_summary` source text) is passed
#            through `redact_text`, which additionally blanks out credit-card-shaped digit runs
#            and common "password:"/"token:"/API-key-shaped" substrings that a structured
#            key/value redaction pass would miss (e.g. inside a customer's own free-text message).
#          - Everything is then truncated to a fixed max length with a visible "...[truncated]"
#            marker, so a summary can never grow unbounded even after redaction.
# Author: CloudDesk Team
# Date: 2026-09-24

import json
import logging
import re
import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AgentRunStatus
from app.models.observability import AgentRun
from app.services.exceptions import NotFoundError

logger = logging.getLogger("clouddesk.services.observability")

INPUT_SUMMARY_MAX_LENGTH: int = 300
OUTPUT_SUMMARY_MAX_LENGTH: int = 300
TOOL_VALUE_MAX_LENGTH: int = 200
ERROR_MESSAGE_MAX_LENGTH: int = 500
TRUNCATION_MARKER: str = "...[truncated]"
REDACTED_PLACEHOLDER: str = "[REDACTED]"

# Mapping-key substrings (case-insensitive) whose VALUE is always redacted, wherever they occur
# in a tool-call argument dict or a tool-result payload.
SENSITIVE_KEY_SUBSTRINGS: frozenset[str] = frozenset(
    {
        "password",
        "secret",
        "token",
        "authorization",
        "api_key",
        "apikey",
        "private_key",
        "card_number",
        "cvv",
        "ssn",
    }
)

# Free-text patterns that a key/value redaction pass would miss because they appear inside plain
# customer-written prose (e.g. "my card is 4111 1111 1111 1111" or "my password is hunter2").
_CARD_NUMBER_PATTERN = re.compile(r"\b(?:\d[ -]?){13,19}\b")
_LABELED_SECRET_PATTERN = re.compile(
    r"\b(password|passwd|pwd|api[_ ]?key|secret|token)\s*[:=]\s*\S+", re.IGNORECASE
)
_BEARER_TOKEN_PATTERN = re.compile(r"\b[A-Za-z0-9_-]{24,}\b")


def truncate(text: str, max_length: int) -> str:
    """Truncate `text` to `max_length` characters, appending a visible truncation marker."""
    if len(text) <= max_length:
        return text
    cutoff = max(max_length - len(TRUNCATION_MARKER), 0)
    return text[:cutoff] + TRUNCATION_MARKER


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(substring in lowered for substring in SENSITIVE_KEY_SUBSTRINGS)


def redact_mapping(data: Any) -> Any:
    """Recursively redact sensitive keys in a dict/list structure. Non-mapping/sequence leaves
    (str/int/float/bool/None) are returned unchanged (truncation happens separately)."""
    if isinstance(data, Mapping):
        return {
            key: (REDACTED_PLACEHOLDER if _is_sensitive_key(str(key)) else redact_mapping(value))
            for key, value in data.items()
        }
    if isinstance(data, Sequence) and not isinstance(data, str | bytes):
        return [redact_mapping(item) for item in data]
    return data


def redact_text(text: str, *, include_generic_tokens: bool = False) -> str:
    """Best-effort redaction of secrets/PII embedded in free-form text (customer messages,
    agent-generated prose) that a structured key/value pass cannot see into.

    `include_generic_tokens` additionally blanks out any long opaque alphanumeric run (24+
    chars), which is a good heuristic for API keys/bearer tokens appearing in raw CUSTOMER text,
    but is deliberately NOT applied to rendered structured output/tool JSON, where a run that
    long is far more likely to be a legitimate id (UUID, transaction reference) than a secret —
    key-based redaction (`redact_mapping`) already covers named secret fields there.
    """
    redacted = _LABELED_SECRET_PATTERN.sub(lambda m: f"{m.group(1)}: {REDACTED_PLACEHOLDER}", text)
    redacted = _CARD_NUMBER_PATTERN.sub(REDACTED_PLACEHOLDER, redacted)
    if include_generic_tokens:
        redacted = _BEARER_TOKEN_PATTERN.sub(REDACTED_PLACEHOLDER, redacted)
    return redacted


def summarize_input(customer_message: str | None) -> str | None:
    """Build a redacted, length-bounded summary of the agent's input text."""
    if not customer_message:
        return None
    return truncate(redact_text(customer_message, include_generic_tokens=True), INPUT_SUMMARY_MAX_LENGTH)


def _to_plain_dict(data: Any) -> Any:
    if isinstance(data, BaseModel):
        return data.model_dump(mode="json")
    return data


def summarize_output(result: Any) -> str | None:
    """Build a redacted, length-bounded, JSON-ish summary of a structured agent result."""
    if result is None:
        return None
    plain = redact_mapping(_to_plain_dict(result))
    try:
        rendered = json.dumps(plain, default=str)
    except TypeError:
        rendered = str(plain)
    return truncate(redact_text(rendered), OUTPUT_SUMMARY_MAX_LENGTH)


def summarize_tool_result(result: Any) -> Any:
    """Redact and truncate one tool's result payload before it is ever held in memory or
    persisted (used by the tracer at the moment a tool call completes)."""
    plain = redact_mapping(_to_plain_dict(result))
    if isinstance(plain, str):
        return truncate(redact_text(plain), TOOL_VALUE_MAX_LENGTH)
    try:
        rendered = json.dumps(plain, default=str)
    except TypeError:
        rendered = str(plain)
    return truncate(rendered, TOOL_VALUE_MAX_LENGTH)


async def create_agent_run(
    session: AsyncSession,
    *,
    ticket_id: uuid.UUID | None,
    thread_id: str,
    agent_name: str,
    start_time: datetime,
    end_time: datetime,
    duration_ms: int,
    status: AgentRunStatus,
    input_summary: str | None,
    output_summary: str | None,
    tool_calls: list[dict[str, Any]],
    tool_results: list[dict[str, Any]],
    error: str | None,
    iteration: int | None,
) -> AgentRun:
    """Persist one `AgentRun` row. Caller (the tracer) is responsible for catching/handling any
    exception raised here so a tracing failure never breaks the real support workflow."""
    agent_run = AgentRun(
        ticket_id=ticket_id,
        thread_id=thread_id,
        agent_name=agent_name,
        start_time=start_time,
        end_time=end_time,
        duration_ms=duration_ms,
        status=status,
        input_summary=input_summary,
        output_summary=output_summary,
        tool_calls=tool_calls,
        tool_results=tool_results,
        error=truncate(error, ERROR_MESSAGE_MAX_LENGTH) if error else None,
        iteration=iteration,
    )
    session.add(agent_run)
    try:
        await session.commit()
    except Exception:
        logger.exception("Failed to commit agent_run for thread %s agent %s", thread_id, agent_name)
        await session.rollback()
        raise
    await session.refresh(agent_run)
    return agent_run


async def get_agent_run(session: AsyncSession, run_id: uuid.UUID) -> AgentRun:
    """Fetch a single AgentRun by id (run_id) or raise NotFoundError."""
    result = await session.execute(select(AgentRun).where(AgentRun.id == run_id))
    agent_run = result.scalar_one_or_none()
    if agent_run is None:
        raise NotFoundError(f"Agent run {run_id} not found")
    return agent_run


async def get_trace_for_ticket(session: AsyncSession, ticket_id: uuid.UUID) -> list[AgentRun]:
    """Return every AgentRun tied to a ticket, in chronological execution order (spec section
    24/26's per-ticket agent trace view)."""
    result = await session.execute(
        select(AgentRun).where(AgentRun.ticket_id == ticket_id).order_by(AgentRun.start_time.asc())
    )
    return list(result.scalars().all())


async def get_trace_for_thread(session: AsyncSession, thread_id: str) -> list[AgentRun]:
    """Return every AgentRun tied to a LangGraph thread, in chronological execution order.

    Used by the Phase 9 customer-facing conversation-status endpoint (spec section 25) to derive
    a live, safe high-level step sequence ("Checking billing", "Preparing resolution", ...) while
    a workflow run is still in progress, keyed by `thread_id` rather than `ticket_id` since a
    ticket's own id is not necessarily known to the caller yet (it is best-effort auto-created at
    the very start of the run — app.graph.graph._create_ticket_if_possible — but that happens
    inside the same background task the caller is polling the status of).
    """
    result = await session.execute(
        select(AgentRun).where(AgentRun.thread_id == thread_id).order_by(AgentRun.start_time.asc())
    )
    return list(result.scalars().all())

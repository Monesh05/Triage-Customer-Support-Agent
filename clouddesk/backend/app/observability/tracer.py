# app/observability/tracer.py
# Purpose: Instrumentation half of Phase 7 (Agent Observability, spec section 24). Provides:
#          (1) `trace_agent_run`, an async context manager wrapping one agent/node execution that
#          captures start/end time and duration, and persists an `AgentRun` row
#          (app.services.observability_service) on exit — success or failure — WITHOUT ever
#          letting a persistence failure propagate out and break the real support workflow; and
#          (2) a lightweight ContextVar-based tool-call collector (`collect_tool_calls` /
#          `record_tool_call`) that lets `app.agents.base.run_tool_using_agent`'s bounded tool
#          loop report which tools it called and their (redacted/truncated) results up to
#          whichever `trace_agent_run` block is currently active, WITHOUT changing
#          `run_tool_using_agent`'s signature or any of its existing callers/tests — the
#          collector is simply a no-op when no trace is active (e.g. every Phase 3 agent unit
#          test that calls `run_billing_agent` etc. directly, outside the graph).
# Author: CloudDesk Team
# Date: 2026-09-24

import logging
import time
import uuid
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.database.session import get_session
from app.models.enums import AgentRunStatus
from app.services import observability_service

logger = logging.getLogger("clouddesk.observability.tracer")

_tool_call_collector: ContextVar[list[dict[str, Any]] | None] = ContextVar(
    "clouddesk_tool_call_collector", default=None
)


@contextmanager
def collect_tool_calls() -> Iterator[list[dict[str, Any]]]:
    """Activate tool-call collection for the duration of the `with` block. Nested/unrelated
    calls to `record_tool_call` outside any active block are silently ignored."""
    collected: list[dict[str, Any]] = []
    token = _tool_call_collector.set(collected)
    try:
        yield collected
    finally:
        _tool_call_collector.reset(token)


def record_tool_call(tool_name: str, args: dict[str, Any], result: Any) -> None:
    """Record one tool invocation for the currently active trace, if any. No-op when called
    outside a `collect_tool_calls()` block (e.g. an agent invoked directly in a unit test)."""
    collected = _tool_call_collector.get()
    if collected is None:
        return
    redacted_args = observability_service.redact_mapping(args) if isinstance(args, dict) else str(args)
    collected.append(
        {"tool": tool_name, "args": redacted_args, "result": observability_service.summarize_tool_result(result)}
    )


@dataclass
class AgentRunRecorder:
    """Mutable handle a node uses, inside a `trace_agent_run` block, to describe what happened."""

    thread_id: str
    ticket_id: uuid.UUID | None
    agent_name: str
    iteration: int | None = None
    input_text: str | None = None
    output_data: Any = None
    error_message: str | None = None
    status: AgentRunStatus = AgentRunStatus.SUCCESS

    def set_input(self, text: str | None) -> None:
        self.input_text = text

    def set_output(self, data: Any) -> None:
        self.output_data = data
        self.status = AgentRunStatus.SUCCESS

    def mark_failure(self, message: str) -> None:
        self.status = AgentRunStatus.FAILURE
        self.error_message = message


@asynccontextmanager
async def trace_agent_run(
    *,
    thread_id: str,
    ticket_id: uuid.UUID | None,
    agent_name: str,
    iteration: int | None = None,
) -> AsyncIterator[AgentRunRecorder]:
    """Time one agent/node execution and persist a redacted `AgentRun` record for it.

    The block's caller is expected to call `recorder.set_input` / `set_output` /
    `mark_failure` itself (nodes already catch `AgentError` explicitly, so this context manager's
    own `except` clause is a safety net for a truly unexpected exception escaping the block, not
    the primary error-reporting path).
    """
    recorder = AgentRunRecorder(thread_id=thread_id, ticket_id=ticket_id, agent_name=agent_name, iteration=iteration)
    start_time = datetime.now(timezone.utc)
    start_perf = time.perf_counter()
    with collect_tool_calls() as tool_call_log:
        try:
            yield recorder
        except Exception as exc:  # noqa: BLE001 - safety net; re-raised unchanged below
            recorder.mark_failure(str(exc))
            raise
        finally:
            end_time = datetime.now(timezone.utc)
            duration_ms = int((time.perf_counter() - start_perf) * 1000)
            await _persist_safely(recorder, tool_call_log, start_time, end_time, duration_ms)


async def _persist_safely(
    recorder: AgentRunRecorder,
    tool_call_log: list[dict[str, Any]],
    start_time: datetime,
    end_time: datetime,
    duration_ms: int,
) -> None:
    """Persist the AgentRun row. A tracing failure is logged and swallowed here — it must never
    take down the customer-facing support workflow (this phase's key reliability property)."""
    try:
        async with get_session() as session:
            await observability_service.create_agent_run(
                session,
                ticket_id=recorder.ticket_id,
                thread_id=recorder.thread_id,
                agent_name=recorder.agent_name,
                start_time=start_time,
                end_time=end_time,
                duration_ms=duration_ms,
                status=recorder.status,
                input_summary=observability_service.summarize_input(recorder.input_text),
                output_summary=observability_service.summarize_output(recorder.output_data),
                tool_calls=[{"tool": entry["tool"], "args": entry["args"]} for entry in tool_call_log],
                tool_results=[{"tool": entry["tool"], "result": entry["result"]} for entry in tool_call_log],
                error=recorder.error_message,
                iteration=recorder.iteration,
            )
    except Exception:  # noqa: BLE001 - see docstring: tracing must degrade gracefully
        logger.exception(
            "agent_run_trace_persist_failed agent=%s thread_id=%s", recorder.agent_name, recorder.thread_id
        )

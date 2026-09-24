# app/schemas/observability.py
# Purpose: Pydantic v2 response schemas for the Phase 7 Agent Observability read API (spec
#          sections 24, 26 — the future "Agent Trace" support-console view). A thin, explicit
#          passthrough of `app.models.observability.AgentRun`: every field it exposes was already
#          redacted/truncated at write time (app.services.observability_service), so no further
#          scrubbing is needed here, but the schema still enumerates fields explicitly rather than
#          exposing the ORM row as-is, so a future internal-only column never leaks by accident.
# Author: CloudDesk Team
# Date: 2026-09-24

import uuid
from datetime import datetime
from typing import Any

from app.models.enums import AgentRunStatus
from app.schemas.common import ORMModel


class AgentRunResponse(ORMModel):
    """One recorded agent/node execution (spec section 24's `AgentRun` field list)."""

    run_id: uuid.UUID
    ticket_id: uuid.UUID | None
    thread_id: str
    agent_name: str
    start_time: datetime
    end_time: datetime
    duration_ms: int
    status: AgentRunStatus
    input_summary: str | None
    output_summary: str | None
    tool_calls: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    error: str | None
    iteration: int | None

    @classmethod
    def from_agent_run(cls, agent_run: Any) -> "AgentRunResponse":
        """Build the response from an `AgentRun` ORM row, mapping its `id` to `run_id` (see
        app.models.observability.AgentRun's docstring for why `id` IS spec section 24's
        `run_id`)."""
        return cls(
            run_id=agent_run.id,
            ticket_id=agent_run.ticket_id,
            thread_id=agent_run.thread_id,
            agent_name=agent_run.agent_name,
            start_time=agent_run.start_time,
            end_time=agent_run.end_time,
            duration_ms=agent_run.duration_ms,
            status=agent_run.status,
            input_summary=agent_run.input_summary,
            output_summary=agent_run.output_summary,
            tool_calls=agent_run.tool_calls,
            tool_results=agent_run.tool_results,
            error=agent_run.error,
            iteration=agent_run.iteration,
        )


class TicketTraceResponse(ORMModel):
    """The ordered agent-execution trace for one ticket (spec section 26's Agent Trace view)."""

    ticket_id: uuid.UUID
    runs: list[AgentRunResponse]

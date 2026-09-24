# app/models/observability.py
# Purpose: SQLAlchemy ORM model for `agent_runs` (spec section 24: Agent Observability) — one
#          persisted record per agent/node execution inside a support-workflow run, distinct from
#          `app.models.audit_log.AuditLog` (that table is the compliance/security trail of
#          sensitive business actions; this table is the engineering trace of the multi-agent
#          system itself, used to answer "what did the agents do, in what order, how long did it
#          take, did it fail" for a given ticket — spec section 26's future Agent Trace view).
# Author: CloudDesk Team
# Date: 2026-09-24

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AgentRunStatus

MAX_AGENT_NAME_LENGTH: int = 50
MAX_THREAD_ID_LENGTH: int = 64


class AgentRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One recorded execution of a single agent/node within a support-workflow run.

    Field-by-field design decisions (documented per this phase's brief):
    - `id` (inherited from `UUIDPrimaryKeyMixin`) IS spec section 24's `run_id`: a distinct
      identifier per AGENT EXECUTION, not per whole workflow. A single support-workflow
      invocation produces many `AgentRun` rows (one per specialist that ran, one per reflection
      iteration of resolution/qa, etc.) — see spec section 24's example trace.
    - `thread_id` correlates every `AgentRun` row produced by one call to
      `run_support_workflow` / `resume_support_workflow` back to the same LangGraph checkpoint
      thread (`SupportState.thread_id`, Phase 5). It is how a workflow-level trace is assembled
      even though `run_id` is per-agent.
    - `ticket_id` links the run to the top-level `support_tickets` row a trace view (spec
      section 26) hangs off of. It is NULLABLE because a workflow run's `customer_id` may not
      resolve to a real ticket (unknown customer id, or ticket auto-creation itself failing) —
      tracing must never require a ticket to exist to record what the agents did.
    - `duration_ms` (not `duration`/seconds) for sub-second precision on typically-fast agent
      calls, consistent naming with a fixed unit rather than an ambiguous float.
    - `input_summary` / `output_summary` / `tool_calls` / `tool_results` are always REDACTED and
      TRUNCATED before being persisted here (see `app.services.observability_service`) — never a
      raw dump of the customer message or tool payloads, which could carry PII or secrets.
    - `error` holds only the (truncated) `AgentError.message` string, never a raw stack trace or
      internal file paths.
    - `iteration` is the reflection-loop iteration this row belongs to (resolution/qa nodes,
      spec section 21); NULL for agents that never loop (triage, billing, account, technical,
      product, escalation).
    """

    __tablename__ = "agent_runs"

    ticket_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("support_tickets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    thread_id: Mapped[str] = mapped_column(String(MAX_THREAD_ID_LENGTH), nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(String(MAX_AGENT_NAME_LENGTH), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[AgentRunStatus] = mapped_column(
        Enum(AgentRunStatus, name="agent_run_status", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    input_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_calls: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    tool_results: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    iteration: Mapped[int | None] = mapped_column(Integer, nullable=True)

    ticket: Mapped["SupportTicket | None"] = relationship()

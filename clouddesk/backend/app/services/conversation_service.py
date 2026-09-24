# app/services/conversation_service.py
# Purpose: Phase 9 (spec section 25) asynchronous execution and status tracking for the
#          customer-facing chat API. A support-workflow run (app.graph.graph.run_support_workflow)
#          takes 20-100+ seconds (multiple sequential LLM calls across triage, parallel
#          specialists, and a bounded resolution/QA reflection loop), which is far too slow for a
#          synchronous request/response — this module launches the run as a detached
#          `asyncio.Task` and keeps a small in-process registry (`ConversationRecord`) that
#          GET /api/v1/conversations/{thread_id} polls.
#
#          Design notes:
#          - The registry is in-memory and per-process, matching the same scope decision already
#            made for the LangGraph checkpointer (`app.graph.graph._CHECKPOINTER`, a `MemorySaver`)
#            — it does not survive a process restart, which is an accepted Phase 9 scope boundary,
#            not an oversight (a durable store is Phase 10 production-hardening work).
#          - Live per-agent progress is NOT read from this registry; it is derived on every poll
#            straight from the Phase 7 `AgentRun` trace rows for the thread (already
#            redacted/truncated at write time — see app.services.observability_service), so no
#            chain-of-thought or raw LLM output is ever exposed here, only a safe agent-name +
#            done/failed marker (spec section 25's explicit "do not expose private chain-of-
#            thought" rule).
#          - The background task wraps `run_support_workflow` in a try/except that can never
#            re-raise: an unhandled exception in a fire-and-forget `asyncio.Task` would otherwise
#            only surface as an "exception was never retrieved" warning when the task is garbage
#            collected, silently losing the failure. Here it is always logged and turned into a
#            `failed` conversation status instead.
# Author: CloudDesk Team
# Date: 2026-09-24

import asyncio
import logging
import uuid
from collections.abc import Coroutine
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from app.graph.graph import run_support_workflow
from app.graph.state import SupportState
from app.services.exceptions import NotFoundError

logger = logging.getLogger("clouddesk.services.conversation")

ConversationStatus = Literal["in_progress", "awaiting_approval", "completed", "escalated", "failed"]

GENERIC_FAILURE_MESSAGE: str = (
    "Something went wrong while processing your request. Please try again shortly, or contact "
    "support if the problem continues."
)


@dataclass
class ConversationRecord:
    """One customer-facing conversation's current status (Phase 9 polling state)."""

    thread_id: str
    customer_id: str
    ticket_id: str | None = None
    status: ConversationStatus = "in_progress"
    final_response: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# Module-level, per-process registry — see module docstring for the deliberate in-memory scope.
_conversations: dict[str, ConversationRecord] = {}

# Strong references to in-flight background tasks: asyncio only holds a weak reference to a task
# created via `create_task`, so without this a task can be garbage-collected mid-run.
_background_tasks: set[asyncio.Task[None]] = set()


def get_conversation(thread_id: str) -> ConversationRecord:
    """Fetch a tracked conversation's current record, or raise NotFoundError."""
    record = _conversations.get(thread_id)
    if record is None:
        raise NotFoundError(f"Conversation {thread_id} not found")
    return record


def _derive_status(final_state: SupportState) -> ConversationStatus:
    """Map a finished/paused SupportState onto the customer-facing status vocabulary."""
    if final_state.get("human_approval_required"):
        return "awaiting_approval"
    if final_state.get("escalation_required"):
        return "escalated"
    return "completed"


def _apply_final_state(thread_id: str, final_state: SupportState) -> None:
    record = _conversations.get(thread_id)
    if record is None:
        return  # Registry entry was never created (should not happen) or has since been evicted.
    record.ticket_id = final_state.get("ticket_id")
    record.status = _derive_status(final_state)
    record.final_response = final_state.get("final_response")


async def _run_and_record(
    thread_id: str,
    customer_id: str,
    customer_message: str,
    conversation_history: list[str] | None,
) -> None:
    """Run the workflow to completion (or its first pause) and update the registry. Never raises
    — a failure here must never crash the event loop or leak an unhandled task exception."""
    try:
        final_state = await run_support_workflow(
            customer_id, customer_message, conversation_history, thread_id=thread_id
        )
        _apply_final_state(thread_id, final_state)
    except Exception:  # noqa: BLE001 - background task boundary: log, never propagate/crash.
        logger.exception("conversation_workflow_failed thread_id=%s", thread_id)
        record = _conversations.get(thread_id)
        if record is not None:
            record.status = "failed"
            record.final_response = GENERIC_FAILURE_MESSAGE


def _launch_background(coro: Coroutine[None, None, None]) -> None:
    task: asyncio.Task[None] = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


def start_conversation(
    customer_id: uuid.UUID, message: str, conversation_history: list[str] | None = None
) -> ConversationRecord:
    """Register a new conversation and launch its support-workflow run in the background.

    Returns immediately with an `in_progress` record carrying a freshly generated `thread_id`;
    `ticket_id` starts `None` and is filled in once the run's best-effort ticket auto-creation
    (app.graph.graph._create_ticket_if_possible) completes.
    """
    thread_id = str(uuid.uuid4())
    record = ConversationRecord(thread_id=thread_id, customer_id=str(customer_id))
    _conversations[thread_id] = record
    _launch_background(_run_and_record(thread_id, str(customer_id), message, conversation_history))
    logger.info("conversation_started thread_id=%s customer_id=%s", thread_id, customer_id)
    return record


def record_resumed_workflow(thread_id: str, final_state: SupportState) -> None:
    """Update a tracked conversation's status after its paused run was resumed (Phase 5's
    resume_support_workflow, invoked by app.api.v1.approvals once a pending action is decided).

    A no-op when `thread_id` was never started through this module's `start_conversation` (e.g.
    an approval created outside the Phase 9 chat API) — the approval flow itself is unaffected
    either way, since it does not depend on this registry.
    """
    if thread_id in _conversations:
        _apply_final_state(thread_id, final_state)

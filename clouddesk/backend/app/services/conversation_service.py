# app/services/conversation_service.py
# Purpose: Phase 9 (spec section 25) asynchronous execution and status tracking for the
#          customer-facing chat API. A support-workflow run (app.graph.graph.run_support_workflow)
#          takes 20-100+ seconds (multiple sequential LLM calls across triage, parallel
#          specialists, and a bounded resolution/QA reflection loop), which is far too slow for a
#          synchronous request/response — this module launches the run as a detached
#          `asyncio.Task` and keeps a small status registry that
#          GET /api/v1/conversations/{thread_id} polls.
#
#          Design notes:
#          - (2026-09-25 production-hardening follow-up) The registry is now the
#            `conversation_records` table (app.models.conversation.ConversationRecord), not an
#            in-process `dict` — closing the gap flagged in the Phase 5 and Phase 9 reports and in
#            README's "Production Deployment" section: a backend restart while a conversation was
#            in progress or paused awaiting approval used to lose track of it entirely (the
#            LangGraph checkpoint itself still had the run's state, but nothing could map a
#            `thread_id` back to its customer/ticket/status/final_response any more).
#
#            A reconstruct-from-existing-data approach (deriving everything from the LangGraph
#            checkpoint + the Phase 7 `AgentRun` trace rows, with no new table) was seriously
#            considered, since it would mean one less overlapping source of truth — the exact
#            failure mode behind the Phase 5-era "status lag" bug (see
#            tests/test_graph_pause_resume.py's regression test for that one). It was rejected
#            here because `status="failed"` and a still-"in_progress" run are NOT reliably
#            distinguishable from the checkpoint alone: a mid-run checkpoint (written after the
#            most recently completed node) and a genuinely-crashed run (the background task raised
#            before any further checkpoint was ever written) look identical from `aget_state`
#            without additionally inspecting `PregelTask.interrupts`/exception internals — a much
#            larger surface for a subtle bug than reusing this module's own already-tested status
#            derivation (`_derive_status`, unchanged from Phase 9) and simply persisting it. Since
#            this table is written by exactly one module (this one) and read by exactly one
#            endpoint (`GET /api/v1/conversations/{thread_id}`), the "two sources of truth" risk
#            that caused the earlier bug does not apply the same way: nothing else ever writes to
#            `conversation_records`, so there is nothing else for it to drift out of sync with.
#          - Every read/write here uses `app.database.session.get_session()` (its own connection),
#            never a caller-supplied request session: this module's writes happen from a detached
#            background task with no request in flight by the time the run finishes or pauses, so
#            it needs its own durable, immediately-committed connection regardless of which
#            request (if any) is reading concurrently — the same reason
#            app.graph.graph._create_ticket_if_possible/_persist_pending_actions already use
#            `get_session()` rather than a request-scoped session.
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
# Date: 2026-09-25

import asyncio
import logging
import uuid
from collections.abc import Coroutine
from typing import Literal

from sqlalchemy import select

from app.database.session import get_session
from app.graph.graph import run_support_workflow
from app.graph.state import SupportState
from app.models.conversation import ConversationRecord
from app.services.exceptions import NotFoundError

logger = logging.getLogger("clouddesk.services.conversation")

ConversationStatus = Literal["in_progress", "awaiting_approval", "completed", "escalated", "failed"]

GENERIC_FAILURE_MESSAGE: str = (
    "Something went wrong while processing your request. Please try again shortly, or contact "
    "support if the problem continues."
)

# Strong references to in-flight background tasks: asyncio only holds a weak reference to a task
# created via `create_task`, so without this a task can be garbage-collected mid-run.
_background_tasks: set[asyncio.Task[None]] = set()


async def drain_background_tasks() -> None:
    """Wait for every currently in-flight background workflow task to finish.

    Test-only helper (see tests/conftest.py): pytest-asyncio gives each test its own event loop,
    and a conversation's background task (launched via `asyncio.create_task` in
    `_launch_background`) can still be running when a test function returns. Left alone, that
    task's DB session/connection outlives the loop it was created on and fails with "attached to
    a different loop" once garbage-collected during a LATER test's loop. Never used by the real
    app, which has no reason to block on a workflow it deliberately made fire-and-forget.
    """
    pending = list(_background_tasks)
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)


async def get_conversation(thread_id: str) -> ConversationRecord:
    """Fetch a tracked conversation's current record, or raise NotFoundError.

    Reads from `conversation_records` directly (see module docstring), so this works whether the
    conversation was started by this same process or by one that has since been restarted.
    """
    async with get_session() as session:
        result = await session.execute(
            select(ConversationRecord).where(ConversationRecord.thread_id == thread_id)
        )
        record = result.scalar_one_or_none()
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


async def _apply_final_state(thread_id: str, final_state: SupportState) -> None:
    """Update a tracked conversation's row from a finished/paused SupportState. A no-op (logged)
    if the row is missing or the update otherwise fails — this must never crash the background
    task or a resume request that called it."""
    try:
        async with get_session() as session:
            result = await session.execute(
                select(ConversationRecord).where(ConversationRecord.thread_id == thread_id)
            )
            record = result.scalar_one_or_none()
            if record is None:
                # Registry entry was never created (should not happen) or has since been evicted.
                logger.warning("conversation_record_missing_on_update thread_id=%s", thread_id)
                return
            record.ticket_id = final_state.get("ticket_id")
            record.status = _derive_status(final_state)
            record.final_response = final_state.get("final_response")
            await session.commit()
    except Exception:  # noqa: BLE001 - background-task/resume boundary: log, never propagate.
        logger.exception("conversation_record_update_failed thread_id=%s", thread_id)


async def _mark_failed(thread_id: str) -> None:
    """Best-effort: mark a tracked conversation as failed after its background run raised."""
    try:
        async with get_session() as session:
            result = await session.execute(
                select(ConversationRecord).where(ConversationRecord.thread_id == thread_id)
            )
            record = result.scalar_one_or_none()
            if record is None:
                return
            record.status = "failed"
            record.final_response = GENERIC_FAILURE_MESSAGE
            await session.commit()
    except Exception:  # noqa: BLE001 - background-task boundary: log, never propagate/crash.
        logger.exception("conversation_record_mark_failed_failed thread_id=%s", thread_id)


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
        await _apply_final_state(thread_id, final_state)
    except Exception:  # noqa: BLE001 - background task boundary: log, never propagate/crash.
        logger.exception("conversation_workflow_failed thread_id=%s", thread_id)
        await _mark_failed(thread_id)


def _launch_background(coro: Coroutine[None, None, None]) -> None:
    task: asyncio.Task[None] = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def start_conversation(
    customer_id: uuid.UUID, message: str, conversation_history: list[str] | None = None
) -> ConversationRecord:
    """Persist a new conversation row and launch its support-workflow run in the background.

    Returns immediately with an `in_progress` record carrying a freshly generated `thread_id`;
    `ticket_id` starts `None` and is filled in once the run's best-effort ticket auto-creation
    (app.graph.graph._create_ticket_if_possible) completes.
    """
    thread_id = str(uuid.uuid4())
    record = ConversationRecord(thread_id=thread_id, customer_id=str(customer_id), status="in_progress")
    async with get_session() as session:
        session.add(record)
        await session.commit()
        await session.refresh(record)
    _launch_background(_run_and_record(thread_id, str(customer_id), message, conversation_history))
    logger.info("conversation_started thread_id=%s customer_id=%s", thread_id, customer_id)
    return record


async def record_resumed_workflow(thread_id: str, final_state: SupportState) -> None:
    """Update a tracked conversation's status after its paused run was resumed (Phase 5's
    resume_support_workflow, invoked by app.api.v1.approvals once a pending action is decided).

    A no-op when `thread_id` was never started through this module's `start_conversation` (e.g.
    an approval created outside the Phase 9 chat API) — the approval flow itself is unaffected
    either way, since it does not depend on this registry.
    """
    await _apply_final_state(thread_id, final_state)

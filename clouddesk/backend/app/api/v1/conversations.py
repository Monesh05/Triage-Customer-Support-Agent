# app/api/v1/conversations.py
# Purpose: REST endpoints for the Phase 9 customer-facing chat API (spec section 25): start a
#          support conversation and poll its live status. `run_support_workflow` takes
#          20-100+ seconds end-to-end (sequential LLM calls across triage, parallel specialists,
#          and a bounded resolution/QA reflection loop) so POST here never awaits it directly —
#          it launches the run as a detached background task (app.services.conversation_service)
#          and returns 202 Accepted immediately with a `thread_id` to poll. Phase 10 (spec
#          section 27): the acting customer id comes from the authenticated token, not the
#          request body — `ConversationStartRequest.customer_id` must match the token's own id
#          (org policy A01: never trust a client-supplied id for authorization), and polling a
#          conversation is only allowed for the customer who started it (or staff).
# Author: CloudDesk Team
# Date: 2026-09-24

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_claims, require_customer_access
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.core.security import AuthRole, TokenClaims
from app.database.session import get_db_session
from app.models.enums import AgentRunStatus
from app.models.observability import AgentRun
from app.schemas.conversation import (
    ConversationStartRequest,
    ConversationStartResponse,
    ConversationStatusResponse,
    ConversationStep,
)
from app.services import conversation_service, observability_service

router = APIRouter(prefix="/conversations", tags=["conversations"])

_FORBIDDEN_DETAIL: str = "You do not have access to this resource"

# Safe, customer-facing labels for each agent/node name persisted in an AgentRun row (spec
# section 25's "✓ Understanding request / ✓ Checking billing / ⟳ Preparing resolution" example).
# Deliberately excludes internal node names never worth surfacing to a customer (finalize,
# await_human_decision — see app.graph.resolution_nodes — are not traced at all).
_AGENT_STEP_LABELS: dict[str, str] = {
    "triage": "Understanding request",
    "billing": "Checking billing",
    "account": "Checking account",
    "technical": "Checking technical details",
    "product": "Checking product documentation",
    "resolution": "Preparing resolution",
    "qa": "Reviewing resolution",
    "escalation": "Escalating to a specialist",
}
_IN_PROGRESS_STEP_LABEL: str = "Finalizing response"


def _step_status(agent_run: AgentRun) -> str:
    return "done" if agent_run.status == AgentRunStatus.SUCCESS else "failed"


def _build_steps(agent_runs: list[AgentRun], overall_status: str) -> list[ConversationStep]:
    """Derive the safe, high-level step sequence from the (already redacted) Phase 7 trace rows
    for this thread. Never includes input/output summaries or tool calls — only an agent's safe
    label and a done/in_progress/failed marker (spec section 25: no chain-of-thought exposure)."""
    steps = [
        ConversationStep(step=_AGENT_STEP_LABELS.get(run.agent_name, run.agent_name), status=_step_status(run))
        for run in agent_runs
    ]
    if overall_status == "in_progress":
        steps.append(ConversationStep(step=_IN_PROGRESS_STEP_LABEL, status="in_progress"))
    return steps


@router.post("", response_model=ConversationStartResponse, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(lambda: get_settings().rate_limit_conversations)
async def start_conversation(
    request: Request,  # noqa: ARG001 - required by slowapi to key the rate limit.
    payload: ConversationStartRequest,
    claims: TokenClaims = Depends(get_current_claims),
) -> ConversationStartResponse:
    """Start a new customer support conversation. Returns immediately; the multi-agent workflow
    runs in the background and its progress/result is available via GET .../{thread_id}.
    """
    require_customer_access(payload.customer_id, claims)
    record = await conversation_service.start_conversation(
        payload.customer_id, payload.message, payload.conversation_history
    )
    ticket_uuid = uuid.UUID(record.ticket_id) if record.ticket_id else None
    return ConversationStartResponse(thread_id=record.thread_id, ticket_id=ticket_uuid, status=record.status)


@router.get("/{thread_id}", response_model=ConversationStatusResponse)
async def read_conversation_status(
    thread_id: str,
    session: AsyncSession = Depends(get_db_session),
    claims: TokenClaims = Depends(get_current_claims),
) -> ConversationStatusResponse:
    """Poll a conversation's current status: safe high-level step progress, and — once the run
    has finished or paused for human approval — the customer-facing `final_response` text.

    Raises a 404 (via the app-wide `NotFoundError` handler) if `thread_id` is unknown, and a 403
    if the caller is neither staff nor the customer who started this conversation.
    """
    record = await conversation_service.get_conversation(thread_id)
    if claims.role != AuthRole.STAFF and str(claims.customer_id) != record.customer_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=_FORBIDDEN_DETAIL)
    agent_runs = await observability_service.get_trace_for_thread(session, thread_id)
    steps = _build_steps(agent_runs, record.status)
    ticket_uuid = uuid.UUID(record.ticket_id) if record.ticket_id else None
    return ConversationStatusResponse(
        thread_id=record.thread_id,
        ticket_id=ticket_uuid,
        status=record.status,
        steps=steps,
        final_response=record.final_response,
    )

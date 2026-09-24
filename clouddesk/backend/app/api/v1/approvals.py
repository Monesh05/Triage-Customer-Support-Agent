# app/api/v1/approvals.py
# Purpose: REST endpoints for the human-in-the-loop approval queue (spec sections 7, 22, 26):
#          list pending (or all) approval requests, read one, and approve/reject it. An
#          approve/reject call executes the real underlying side effect via
#          app.services.approval_service, and — when the action came from a paused support
#          workflow run — resumes that exact run via app.graph.graph.resume_support_workflow so
#          the ticket's conversation actually concludes. When that paused thread was started
#          through the Phase 9 chat API (spec section 25), also updates its conversation-status
#          registry (app.services.conversation_service) so a customer's next status poll reflects
#          the resumed outcome instead of staying stuck on "awaiting_approval" forever.
# Author: CloudDesk Team
# Date: 2026-09-24

import logging
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.graph.graph import resume_support_workflow
from app.models.approval import ApprovalRequest
from app.models.enums import ApprovalStatus
from app.schemas.approval import (
    ApprovalDecisionRequest,
    ApprovalDecisionResponse,
    ApprovalRequestResponse,
)
from app.services import approval_service, conversation_service
from app.services.exceptions import InvalidStateError

logger = logging.getLogger("clouddesk.api.approvals")

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalRequestResponse])
async def list_approvals(
    include_decided: bool = False, session: AsyncSession = Depends(get_db_session)
) -> list[ApprovalRequestResponse]:
    """List approval requests, most recent first. By default only PENDING ones are returned;
    pass `?include_decided=true` for the full history (spec section 26's Approval Queue).
    """
    status_filter = None if include_decided else ApprovalStatus.PENDING
    requests = await approval_service.list_pending_actions(session, status_filter)
    return [ApprovalRequestResponse.model_validate(r) for r in requests]


@router.get("/{action_id}", response_model=ApprovalRequestResponse)
async def read_approval(
    action_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)
) -> ApprovalRequestResponse:
    """Return a single approval request's detail."""
    approval_request = await approval_service.get_pending_action(session, action_id)
    return ApprovalRequestResponse.model_validate(approval_request)


async def _maybe_resume_thread(
    session: AsyncSession, approval_request: ApprovalRequest
) -> tuple[bool, str | None]:
    """After a decision on one action, resume the paused graph run for its thread ONLY once
    every action belonging to that same thread has been decided (a paused run may have surfaced
    more than one pending action in the same batch; resuming early would let the graph continue
    before all of its outstanding decisions are known).
    """
    sibling_actions = await approval_service.list_actions_for_thread(session, approval_request.thread_id)
    if any(a.status == ApprovalStatus.PENDING for a in sibling_actions):
        return False, None

    decision = {
        "actions": [
            {"action_id": str(a.id), "status": a.status.value}
            for a in sibling_actions
        ]
    }
    try:
        final_state = await resume_support_workflow(approval_request.thread_id, decision)
    except InvalidStateError:
        # No matching paused run (e.g. this approval request predates Phase 5's graph wiring, or
        # was created outside a graph run entirely) — the decision itself is still fully valid.
        logger.info(
            "approval_decided_no_paused_thread thread_id=%s action_id=%s",
            approval_request.thread_id, approval_request.id,
        )
        return False, None
    conversation_service.record_resumed_workflow(approval_request.thread_id, final_state)
    return True, final_state.get("final_response")


@router.post("/{action_id}/approve", response_model=ApprovalDecisionResponse)
async def approve_approval(
    action_id: uuid.UUID,
    payload: ApprovalDecisionRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ApprovalDecisionResponse:
    """Approve a pending action: execute its real side effect and, if possible, resume the
    paused support workflow it came from.
    """
    approval_request, executed = await approval_service.approve_action(session, action_id, payload.actor)
    logger.info("approval_approved action_id=%s actor=%s executed=%s", action_id, payload.actor, executed)

    resumed, final_response = await _maybe_resume_thread(session, approval_request)
    return ApprovalDecisionResponse(
        approval_request=ApprovalRequestResponse.model_validate(approval_request),
        executed=executed,
        workflow_resumed=resumed,
        final_response=final_response,
    )


@router.post("/{action_id}/reject", response_model=ApprovalDecisionResponse)
async def reject_approval(
    action_id: uuid.UUID,
    payload: ApprovalDecisionRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ApprovalDecisionResponse:
    """Reject a pending action: never executes it, but still resumes the paused workflow (if
    any) so the customer gets an explanatory response instead of staying stuck pending forever.
    """
    approval_request = await approval_service.reject_action(session, action_id, payload.actor, payload.reason)
    logger.info("approval_rejected action_id=%s actor=%s", action_id, payload.actor)

    resumed, final_response = await _maybe_resume_thread(session, approval_request)
    return ApprovalDecisionResponse(
        approval_request=ApprovalRequestResponse.model_validate(approval_request),
        executed=False,
        workflow_resumed=resumed,
        final_response=final_response,
    )

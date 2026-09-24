# app/services/approval_service.py
# Purpose: Business logic for the generic human-in-the-loop approval queue (spec section 22).
#          Persists one `ApprovalRequest` row per agent-recommended action that requires human
#          sign-off, lists pending/decided rows for the future approval-queue UI (spec section
#          26), and executes the REAL underlying side effect when an action is approved (never
#          just flipping a status flag, per spec section 27) via app/services/payment_service.py
#          for refund-shaped actions. Every approve/reject decision is audited.
# Author: CloudDesk Team
# Date: 2026-09-24

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval import ApprovalRequest
from app.models.enums import ApprovalStatus, AuditActionType, RefundRequestStatus
from app.models.payment import RefundRequest
from app.services import payment_service
from app.services.audit_service import record_audit
from app.services.exceptions import InvalidStateError, NotFoundError

logger = logging.getLogger("clouddesk.services.approval")

REFUND_AGENT_NAME: str = "billing"


async def _find_matching_refund_request(
    session: AsyncSession, customer_id: uuid.UUID, amount: Decimal | None
) -> RefundRequest | None:
    """Best-effort link from a billing agent's recommended action to a real, already-created
    PENDING_APPROVAL refund request for the same customer/amount (see app/models/approval.py's
    module docstring: `RecommendedAction` carries no direct refund-request id). Returns None if
    no unambiguous match exists — callers must not assume a link is always available.
    """
    if amount is None:
        return None
    result = await session.execute(
        select(RefundRequest).where(
            RefundRequest.customer_id == customer_id,
            RefundRequest.status == RefundRequestStatus.PENDING_APPROVAL,
            RefundRequest.amount == amount,
        )
    )
    matches = result.scalars().all()
    return matches[0] if len(matches) == 1 else None


async def _commit_and_refresh(
    session: AsyncSession, entity: ApprovalRequest, error_context: str
) -> None:
    """Shared commit/rollback/refresh epilogue for every mutating operation in this module."""
    try:
        await session.commit()
    except Exception:
        logger.exception("Failed to commit %s", error_context)
        await session.rollback()
        raise
    await session.refresh(entity)


def _parse_amount(action: dict[str, Any]) -> Decimal | None:
    amount_raw = action.get("amount")
    if amount_raw is None:
        return None
    try:
        return Decimal(str(amount_raw))
    except InvalidOperation:
        return None


async def create_pending_action(
    session: AsyncSession,
    customer_id: uuid.UUID,
    thread_id: str,
    agent_name: str,
    action: dict[str, Any],
) -> ApprovalRequest:
    """Persist one pending human-approval action produced by the support graph's finalize step.

    `action` is one entry of `SupportState.pending_actions` (spec section 22 /
    app/graph/nodes.py's `_collect_pending_actions`): {"agent", "action", "amount",
    "requires_approval", ...}.
    """
    amount = _parse_amount(action)

    refund_request: RefundRequest | None = None
    if agent_name == REFUND_AGENT_NAME:
        refund_request = await _find_matching_refund_request(session, customer_id, amount)

    approval_request = ApprovalRequest(
        customer_id=customer_id,
        thread_id=thread_id,
        agent_name=agent_name,
        action_description=str(action.get("action", "")),
        amount=amount,
        payload=action,
        status=ApprovalStatus.PENDING,
        refund_request_id=refund_request.id if refund_request else None,
    )
    session.add(approval_request)
    await _commit_and_refresh(session, approval_request, f"pending action for thread {thread_id}")

    logger.info(
        "pending_action_created id=%s thread_id=%s agent=%s linked_refund=%s",
        approval_request.id, thread_id, agent_name, bool(refund_request),
    )
    return approval_request


async def get_pending_action(session: AsyncSession, action_id: uuid.UUID) -> ApprovalRequest:
    """Fetch a single approval request by id or raise NotFoundError."""
    result = await session.execute(select(ApprovalRequest).where(ApprovalRequest.id == action_id))
    approval_request = result.scalar_one_or_none()
    if approval_request is None:
        raise NotFoundError(f"Approval request {action_id} not found")
    return approval_request


async def list_pending_actions(
    session: AsyncSession, status_filter: ApprovalStatus | None = ApprovalStatus.PENDING
) -> list[ApprovalRequest]:
    """List approval requests, most recent first. Defaults to only PENDING; pass None for all."""
    query = select(ApprovalRequest).order_by(ApprovalRequest.created_at.desc())
    if status_filter is not None:
        query = query.where(ApprovalRequest.status == status_filter)
    result = await session.execute(query)
    return list(result.scalars().all())


async def list_actions_for_thread(session: AsyncSession, thread_id: str) -> list[ApprovalRequest]:
    """All approval requests tied to one paused graph run, most recent first."""
    result = await session.execute(
        select(ApprovalRequest)
        .where(ApprovalRequest.thread_id == thread_id)
        .order_by(ApprovalRequest.created_at.desc())
    )
    return list(result.scalars().all())


def _assert_pending(approval_request: ApprovalRequest) -> None:
    if approval_request.status != ApprovalStatus.PENDING:
        raise InvalidStateError(
            f"Approval request {approval_request.id} has status={approval_request.status.value}; "
            "it has already been decided"
        )


async def _execute_linked_refund_if_any(
    session: AsyncSession, approval_request: ApprovalRequest, approved_by: str
) -> bool:
    """Execute the real backing refund when this approval is linked to one. Returns whether an
    actual side effect happened, so the caller never claims more than really occurred.
    """
    if approval_request.refund_request_id is None:
        logger.warning(
            "pending_action_approved_without_execution id=%s agent=%s reason=no_linked_record",
            approval_request.id, approval_request.agent_name,
        )
        return False
    await payment_service.approve_refund_request(session, approval_request.refund_request_id, approved_by)
    return True


async def approve_action(
    session: AsyncSession, action_id: uuid.UUID, approved_by: str
) -> tuple[ApprovalRequest, bool]:
    """Approve a pending action and execute its real side effect where one exists.

    Returns `(approval_request, executed)`: `executed` is True only when a concrete backing
    operation (currently: a linked refund request) was actually carried out. An action with no
    automated execution path (e.g. a recommendation with no linked record) is still recorded as
    APPROVED, but `executed=False` so callers never claim more happened than actually did.

    Raises:
        NotFoundError: if the approval request does not exist.
        InvalidStateError: if it was already approved/rejected.
    """
    approval_request = await get_pending_action(session, action_id)
    _assert_pending(approval_request)

    executed = await _execute_linked_refund_if_any(session, approval_request, approved_by)

    approval_request.status = ApprovalStatus.APPROVED
    approval_request.decided_by = approved_by
    approval_request.decided_at = datetime.now(timezone.utc)

    record_audit(
        session, approval_request.customer_id, AuditActionType.PENDING_ACTION_APPROVED, approved_by,
        {"action_id": str(approval_request.id), "agent": approval_request.agent_name, "executed": executed},
    )

    await _commit_and_refresh(session, approval_request, f"approval for action {action_id}")
    logger.info("pending_action_decided id=%s decision=approved executed=%s", action_id, executed)
    return approval_request, executed


async def reject_action(
    session: AsyncSession, action_id: uuid.UUID, rejected_by: str, reason: str | None
) -> ApprovalRequest:
    """Reject a pending action. Never executes the underlying side effect.

    Raises:
        NotFoundError: if the approval request does not exist.
        InvalidStateError: if it was already approved/rejected.
    """
    approval_request = await get_pending_action(session, action_id)
    _assert_pending(approval_request)

    if approval_request.refund_request_id is not None:
        await payment_service.reject_refund_request(
            session, approval_request.refund_request_id, rejected_by, reason
        )

    approval_request.status = ApprovalStatus.REJECTED
    approval_request.decided_by = rejected_by
    approval_request.decided_at = datetime.now(timezone.utc)
    approval_request.rejection_reason = reason

    record_audit(
        session, approval_request.customer_id, AuditActionType.PENDING_ACTION_REJECTED, rejected_by,
        {"action_id": str(approval_request.id), "agent": approval_request.agent_name, "reason": reason or ""},
    )

    await _commit_and_refresh(session, approval_request, f"rejection for action {action_id}")
    logger.info("pending_action_decided id=%s decision=rejected", action_id)
    return approval_request

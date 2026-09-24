# app/services/payment_service.py
# Purpose: Business logic for payment retrieval, refund-amount calculation, and creation of
#          refund request records. Refunds require human approval before execution (spec
#          section 22). Phase 5 adds `approve_refund_request`/`reject_refund_request`, the only
#          place a refund is ever actually executed (payment marked REFUNDED) — always driven by
#          a real human decision recorded via app/services/approval_service.py, never
#          automatically.
# Author: CloudDesk Team
# Date: 2026-09-24

import logging
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AuditActionType, PaymentStatus, RefundRequestStatus
from app.models.payment import Payment, RefundRequest
from app.services.audit_service import record_audit
from app.services.exceptions import InvalidStateError, NotFoundError

logger = logging.getLogger(__name__)


async def get_payments_by_customer(
    session: AsyncSession, customer_id: uuid.UUID
) -> list[Payment]:
    """Fetch all payments for a customer, most recent first."""
    result = await session.execute(
        select(Payment)
        .where(Payment.customer_id == customer_id)
        .order_by(Payment.created_at.desc())
    )
    payments = list(result.scalars().all())
    if not payments:
        raise NotFoundError(f"No payments found for customer {customer_id}")
    return payments


async def get_payment_by_id(session: AsyncSession, payment_id: uuid.UUID) -> Payment:
    """Fetch a single payment by id or raise NotFoundError."""
    result = await session.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()
    if payment is None:
        raise NotFoundError(f"Payment {payment_id} not found")
    return payment


def calculate_refund_amount(payment: Payment) -> Decimal:
    """Calculate the refundable amount for a payment (full amount, for succeeded payments)."""
    return Decimal(str(payment.amount))


async def find_duplicate_payments(
    session: AsyncSession, customer_id: uuid.UUID
) -> list[list[Payment]]:
    """Group a customer's succeeded payments by (subscription, billing period start), and
    return only the groups containing more than one payment (duplicate-charge detection).
    """
    payments = await get_payments_by_customer(session, customer_id)
    succeeded = [p for p in payments if p.status == PaymentStatus.SUCCEEDED]

    groups: dict[tuple[uuid.UUID, str], list[Payment]] = {}
    for payment in succeeded:
        key = (payment.subscription_id, payment.billing_period_start.isoformat())
        groups.setdefault(key, []).append(payment)

    return [group for group in groups.values() if len(group) > 1]


def _assert_refundable(payment: Payment) -> None:
    if payment.status != PaymentStatus.SUCCEEDED:
        raise InvalidStateError(
            f"Payment {payment.id} has status={payment.status.value}; only succeeded "
            "payments can be refunded"
        )


async def create_refund_request(
    session: AsyncSession, payment_id: uuid.UUID, reason: str, actor: str
) -> RefundRequest:
    """Create a pending-approval refund request for a payment.

    Raises:
        NotFoundError: if the payment does not exist.
        InvalidStateError: if the payment was not successful (nothing to refund).
    """
    payment = await get_payment_by_id(session, payment_id)
    _assert_refundable(payment)

    amount = calculate_refund_amount(payment)
    refund_request = RefundRequest(
        payment_id=payment.id,
        customer_id=payment.customer_id,
        amount=amount,
        reason=reason,
        status=RefundRequestStatus.PENDING_APPROVAL,
    )
    session.add(refund_request)

    record_audit(
        session, payment.customer_id, AuditActionType.REFUND_REQUEST_CREATED, actor,
        {"payment_id": str(payment.id), "amount": str(amount), "reason": reason},
    )

    try:
        await session.commit()
    except Exception:
        logger.exception("Failed to commit refund request for payment %s", payment_id)
        await session.rollback()
        raise

    await session.refresh(refund_request)
    logger.info("Refund request %s created for payment %s", refund_request.id, payment_id)
    return refund_request


async def get_refund_request_by_id(
    session: AsyncSession, refund_request_id: uuid.UUID
) -> RefundRequest:
    """Fetch a single refund request by id or raise NotFoundError."""
    result = await session.execute(
        select(RefundRequest).where(RefundRequest.id == refund_request_id)
    )
    refund_request = result.scalar_one_or_none()
    if refund_request is None:
        raise NotFoundError(f"Refund request {refund_request_id} not found")
    return refund_request


def _assert_pending_approval(refund_request: RefundRequest) -> None:
    if refund_request.status != RefundRequestStatus.PENDING_APPROVAL:
        raise InvalidStateError(
            f"Refund request {refund_request.id} has status={refund_request.status.value}; "
            "only a pending-approval refund request can be approved or rejected"
        )


async def approve_refund_request(
    session: AsyncSession, refund_request_id: uuid.UUID, approved_by: str
) -> RefundRequest:
    """Approve a pending refund request and ACTUALLY execute it: the underlying payment is
    marked REFUNDED in the same transaction. This is the only code path that ever transitions a
    payment to REFUNDED (spec section 27: never claim an action succeeded unless it happened).

    Raises:
        NotFoundError: if the refund request does not exist.
        InvalidStateError: if it is not currently PENDING_APPROVAL (e.g. already decided).
    """
    refund_request = await get_refund_request_by_id(session, refund_request_id)
    _assert_pending_approval(refund_request)

    payment = await get_payment_by_id(session, refund_request.payment_id)
    payment.status = PaymentStatus.REFUNDED
    refund_request.status = RefundRequestStatus.COMPLETED

    record_audit(
        session, refund_request.customer_id, AuditActionType.REFUND_REQUEST_APPROVED, approved_by,
        {"refund_request_id": str(refund_request.id), "payment_id": str(payment.id)},
    )

    try:
        await session.commit()
    except Exception:
        logger.exception("Failed to commit refund approval for %s", refund_request_id)
        await session.rollback()
        raise

    await session.refresh(refund_request)
    logger.info("Refund request %s approved and executed by %s", refund_request.id, approved_by)
    return refund_request


async def reject_refund_request(
    session: AsyncSession, refund_request_id: uuid.UUID, rejected_by: str, reason: str | None
) -> RefundRequest:
    """Reject a pending refund request. The underlying payment is left untouched.

    Raises:
        NotFoundError: if the refund request does not exist.
        InvalidStateError: if it is not currently PENDING_APPROVAL.
    """
    refund_request = await get_refund_request_by_id(session, refund_request_id)
    _assert_pending_approval(refund_request)

    refund_request.status = RefundRequestStatus.REJECTED

    record_audit(
        session, refund_request.customer_id, AuditActionType.REFUND_REQUEST_REJECTED, rejected_by,
        {"refund_request_id": str(refund_request.id), "reason": reason or ""},
    )

    try:
        await session.commit()
    except Exception:
        logger.exception("Failed to commit refund rejection for %s", refund_request_id)
        await session.rollback()
        raise

    await session.refresh(refund_request)
    logger.info("Refund request %s rejected by %s", refund_request.id, rejected_by)
    return refund_request

# app/services/payment_service.py
# Purpose: Business logic for payment retrieval, refund-amount calculation, and creation of
#          refund request records. Refunds require human approval before execution (spec
#          section 22), so this service only ever creates a PENDING_APPROVAL record — it
#          never marks a payment as refunded itself.
# Author: CloudDesk Team
# Date: 2026-09-21

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

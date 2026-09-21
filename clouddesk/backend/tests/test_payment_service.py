# tests/test_payment_service.py
# Purpose: Unit tests for app.services.payment_service — duplicate-payment detection,
#          refund-amount calculation, and refund-request creation (happy path, invalid
#          state for a failed payment, and not-found for an unknown payment).
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PaymentStatus, RefundRequestStatus
from app.models.subscription import Subscription
from app.services.payment_service import (
    calculate_refund_amount,
    create_refund_request,
    find_duplicate_payments,
)
from app.services.exceptions import InvalidStateError, NotFoundError
from tests.conftest import new_id
from tests.factories import create_customer_with_account, create_org_and_plan, create_payment

_PERIOD = datetime(2026, 9, 1, tzinfo=timezone.utc)


async def _get_subscription(db_session: AsyncSession, customer_id: uuid.UUID) -> Subscription:
    result = await db_session.execute(select(Subscription).where(Subscription.customer_id == customer_id))
    return result.scalar_one()


async def test_find_duplicate_payments_detects_double_charge(db_session: AsyncSession) -> None:
    org, _free, pro = await create_org_and_plan(db_session)
    customer = await create_customer_with_account(db_session, org, pro)
    subscription = await _get_subscription(db_session, customer.id)

    await create_payment(db_session, customer, subscription.id, 49, PaymentStatus.SUCCEEDED, _PERIOD)
    await create_payment(db_session, customer, subscription.id, 49, PaymentStatus.SUCCEEDED, _PERIOD)

    duplicates = await find_duplicate_payments(db_session, customer.id)

    assert len(duplicates) == 1
    assert len(duplicates[0]) == 2


async def test_find_duplicate_payments_no_duplicates_for_single_payment(db_session: AsyncSession) -> None:
    org, _free, pro = await create_org_and_plan(db_session)
    customer = await create_customer_with_account(db_session, org, pro)
    subscription = await _get_subscription(db_session, customer.id)

    await create_payment(db_session, customer, subscription.id, 49, PaymentStatus.SUCCEEDED, _PERIOD)

    duplicates = await find_duplicate_payments(db_session, customer.id)

    assert duplicates == []


def test_calculate_refund_amount_matches_payment_amount() -> None:
    class _FakePayment:
        amount = 49.00

    assert calculate_refund_amount(_FakePayment()) == Decimal("49.0")


async def test_create_refund_request_happy_path(db_session: AsyncSession) -> None:
    org, _free, pro = await create_org_and_plan(db_session)
    customer = await create_customer_with_account(db_session, org, pro)
    subscription = await _get_subscription(db_session, customer.id)
    payment = await create_payment(db_session, customer, subscription.id, 49, PaymentStatus.SUCCEEDED, _PERIOD)

    refund = await create_refund_request(db_session, payment.id, reason="duplicate charge", actor="test")

    assert refund.status == RefundRequestStatus.PENDING_APPROVAL
    assert refund.amount == Decimal("49.00")


async def test_create_refund_request_fails_for_non_succeeded_payment(db_session: AsyncSession) -> None:
    org, _free, pro = await create_org_and_plan(db_session)
    customer = await create_customer_with_account(db_session, org, pro)
    subscription = await _get_subscription(db_session, customer.id)
    payment = await create_payment(db_session, customer, subscription.id, 49, PaymentStatus.FAILED, _PERIOD)

    with pytest.raises(InvalidStateError):
        await create_refund_request(db_session, payment.id, reason="n/a", actor="test")


async def test_create_refund_request_unknown_payment_raises_not_found(db_session: AsyncSession) -> None:
    with pytest.raises(NotFoundError):
        await create_refund_request(db_session, new_id(), reason="n/a", actor="test")

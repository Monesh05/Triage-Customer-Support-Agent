# tests/test_approval_service.py
# Purpose: Unit tests for app.services.approval_service (spec section 22): creating a pending
#          action, approving one linked to a real refund request (asserts the refund/payment are
#          ACTUALLY transitioned, not just the approval row), rejecting one (asserts nothing was
#          executed), double-decision -> InvalidStateError, and approve/reject of an unknown
#          action -> NotFoundError.
# Author: CloudDesk Team
# Date: 2026-09-24

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ApprovalStatus, PaymentStatus, RefundRequestStatus
from app.services.approval_service import (
    approve_action,
    create_pending_action,
    get_pending_action,
    list_pending_actions,
    reject_action,
)
from app.services.exceptions import InvalidStateError, NotFoundError
from app.services.payment_service import create_refund_request, get_payment_by_id
from tests.conftest import new_id
from tests.factories import create_customer_with_account, create_org_and_plan, create_payment

_PERIOD = datetime(2026, 9, 1, tzinfo=timezone.utc)
_THREAD_ID = "thread-abc-123"


async def _billing_action(amount: float = 49.0) -> dict[str, object]:
    return {"agent": "billing", "action": "Refund duplicate payment", "amount": amount, "requires_approval": True}


async def test_create_pending_action_links_matching_refund_request(db_session: AsyncSession) -> None:
    org, _free, pro = await create_org_and_plan(db_session)
    customer = await create_customer_with_account(db_session, org, pro)
    payment = await create_payment(db_session, customer, customer.subscriptions[0].id, 49, PaymentStatus.SUCCEEDED, _PERIOD)
    refund = await create_refund_request(db_session, payment.id, reason="duplicate", actor="billing_agent")

    approval_request = await create_pending_action(
        db_session, customer.id, _THREAD_ID, "billing", await _billing_action(49.0)
    )

    assert approval_request.status == ApprovalStatus.PENDING
    assert approval_request.refund_request_id == refund.id
    assert approval_request.amount == Decimal("49.0")


async def test_create_pending_action_without_matching_refund_leaves_link_unset(db_session: AsyncSession) -> None:
    org, _free, pro = await create_org_and_plan(db_session)
    customer = await create_customer_with_account(db_session, org, pro)

    approval_request = await create_pending_action(
        db_session, customer.id, _THREAD_ID, "account", {"agent": "account", "action": "Unlock account", "amount": None, "requires_approval": True}
    )

    assert approval_request.refund_request_id is None
    assert approval_request.agent_name == "account"


async def test_approve_action_executes_linked_refund(db_session: AsyncSession) -> None:
    org, _free, pro = await create_org_and_plan(db_session)
    customer = await create_customer_with_account(db_session, org, pro)
    payment = await create_payment(db_session, customer, customer.subscriptions[0].id, 49, PaymentStatus.SUCCEEDED, _PERIOD)
    refund = await create_refund_request(db_session, payment.id, reason="duplicate", actor="billing_agent")
    approval_request = await create_pending_action(
        db_session, customer.id, _THREAD_ID, "billing", await _billing_action(49.0)
    )

    decided, executed = await approve_action(db_session, approval_request.id, approved_by="ops_lead")

    assert executed is True
    assert decided.status == ApprovalStatus.APPROVED
    assert decided.decided_by == "ops_lead"

    refreshed_payment = await get_payment_by_id(db_session, payment.id)
    assert refreshed_payment.status == PaymentStatus.REFUNDED
    await db_session.refresh(refund)
    assert refund.status == RefundRequestStatus.COMPLETED


async def test_approve_action_without_linked_record_does_not_claim_execution(db_session: AsyncSession) -> None:
    org, _free, pro = await create_org_and_plan(db_session)
    customer = await create_customer_with_account(db_session, org, pro)
    approval_request = await create_pending_action(
        db_session, customer.id, _THREAD_ID, "account",
        {"agent": "account", "action": "Unlock account", "amount": None, "requires_approval": True},
    )

    decided, executed = await approve_action(db_session, approval_request.id, approved_by="ops_lead")

    assert executed is False
    assert decided.status == ApprovalStatus.APPROVED


async def test_reject_action_does_not_execute_linked_refund(db_session: AsyncSession) -> None:
    org, _free, pro = await create_org_and_plan(db_session)
    customer = await create_customer_with_account(db_session, org, pro)
    payment = await create_payment(db_session, customer, customer.subscriptions[0].id, 49, PaymentStatus.SUCCEEDED, _PERIOD)
    await create_refund_request(db_session, payment.id, reason="duplicate", actor="billing_agent")
    approval_request = await create_pending_action(
        db_session, customer.id, _THREAD_ID, "billing", await _billing_action(49.0)
    )

    decided = await reject_action(db_session, approval_request.id, rejected_by="ops_lead", reason="not eligible")

    assert decided.status == ApprovalStatus.REJECTED
    assert decided.rejection_reason == "not eligible"
    refreshed_payment = await get_payment_by_id(db_session, payment.id)
    assert refreshed_payment.status == PaymentStatus.SUCCEEDED


async def test_double_approve_raises_invalid_state(db_session: AsyncSession) -> None:
    org, _free, pro = await create_org_and_plan(db_session)
    customer = await create_customer_with_account(db_session, org, pro)
    approval_request = await create_pending_action(
        db_session, customer.id, _THREAD_ID, "account",
        {"agent": "account", "action": "Unlock account", "amount": None, "requires_approval": True},
    )
    await approve_action(db_session, approval_request.id, approved_by="ops_lead")

    with pytest.raises(InvalidStateError):
        await approve_action(db_session, approval_request.id, approved_by="ops_lead")


async def test_double_reject_raises_invalid_state(db_session: AsyncSession) -> None:
    org, _free, pro = await create_org_and_plan(db_session)
    customer = await create_customer_with_account(db_session, org, pro)
    approval_request = await create_pending_action(
        db_session, customer.id, _THREAD_ID, "account",
        {"agent": "account", "action": "Unlock account", "amount": None, "requires_approval": True},
    )
    await reject_action(db_session, approval_request.id, rejected_by="ops_lead", reason=None)

    with pytest.raises(InvalidStateError):
        await reject_action(db_session, approval_request.id, rejected_by="ops_lead", reason=None)


async def test_approve_unknown_action_raises_not_found(db_session: AsyncSession) -> None:
    with pytest.raises(NotFoundError):
        await approve_action(db_session, new_id(), approved_by="ops_lead")


async def test_reject_unknown_action_raises_not_found(db_session: AsyncSession) -> None:
    with pytest.raises(NotFoundError):
        await reject_action(db_session, new_id(), rejected_by="ops_lead", reason=None)


async def test_list_pending_actions_defaults_to_pending_only(db_session: AsyncSession) -> None:
    org, _free, pro = await create_org_and_plan(db_session)
    customer = await create_customer_with_account(db_session, org, pro)
    pending = await create_pending_action(
        db_session, customer.id, _THREAD_ID, "account",
        {"agent": "account", "action": "Unlock account", "amount": None, "requires_approval": True},
    )
    decided = await create_pending_action(
        db_session, customer.id, "thread-2", "account",
        {"agent": "account", "action": "Change security setting", "amount": None, "requires_approval": True},
    )
    await reject_action(db_session, decided.id, rejected_by="ops_lead", reason=None)

    results = await list_pending_actions(db_session)

    result_ids = {r.id for r in results}
    assert pending.id in result_ids
    assert decided.id not in result_ids


async def test_get_pending_action_unknown_raises_not_found(db_session: AsyncSession) -> None:
    with pytest.raises(NotFoundError):
        await get_pending_action(db_session, new_id())

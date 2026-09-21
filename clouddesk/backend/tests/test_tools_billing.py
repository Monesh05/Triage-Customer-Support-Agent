# tests/test_tools_billing.py
# Purpose: Tests for app.tools.billing — subscriptions, payment history, invoices, refund
#          calculation/creation, and billing policy lookup. Uses `committed_session` because
#          these tools open their own DB connection via app.database.session.get_session(),
#          separate from the rolled-back `db_session` transaction.
# Author: CloudDesk Team
# Date: 2026-09-21

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import InvoiceStatus, PaymentStatus
from app.models.invoice import Invoice
from app.models.policy import SupportPolicy
from app.tools import billing
from tests.conftest import new_id
from tests.factories import create_customer_with_account, create_org_and_plan, create_payment

_PERIOD = datetime(2026, 9, 1, tzinfo=timezone.utc)


async def _register(committed_session: AsyncSession, org) -> None:
    committed_session.info["created_org_ids"].append(org.id)


async def test_get_subscription_happy_path(committed_session: AsyncSession) -> None:
    org, _free, pro = await create_org_and_plan(committed_session)
    customer = await create_customer_with_account(committed_session, org, pro)
    await committed_session.commit()
    await _register(committed_session, org)

    result = await billing.get_subscription(customer.id)

    assert result.success is True
    assert result.data is not None
    assert result.data[0].plan.name == pro.name


async def test_get_subscription_not_found(committed_session: AsyncSession) -> None:
    result = await billing.get_subscription(new_id())

    assert result.success is False
    assert result.error is not None


async def test_get_payment_history_happy_path(committed_session: AsyncSession) -> None:
    org, _free, pro = await create_org_and_plan(committed_session)
    customer = await create_customer_with_account(committed_session, org, pro)
    subscription = customer.subscriptions[0]
    await create_payment(committed_session, customer, subscription.id, 49, PaymentStatus.SUCCEEDED, _PERIOD)
    await committed_session.commit()
    await _register(committed_session, org)

    result = await billing.get_payment_history(customer.id)

    assert result.success is True
    assert len(result.data) == 1
    assert result.data[0].amount == 49


async def test_get_invoice_not_found(committed_session: AsyncSession) -> None:
    result = await billing.get_invoice(new_id())

    assert result.success is False


async def test_get_invoice_happy_path(committed_session: AsyncSession) -> None:
    org, _free, pro = await create_org_and_plan(committed_session)
    customer = await create_customer_with_account(committed_session, org, pro)
    subscription = customer.subscriptions[0]
    committed_session.add(
        Invoice(
            customer_id=customer.id, subscription_id=subscription.id, amount=49,
            status=InvoiceStatus.PAID, issued_at=_PERIOD, due_at=_PERIOD,
        )
    )
    await committed_session.commit()
    await _register(committed_session, org)

    result = await billing.get_invoice(customer.id)

    assert result.success is True
    assert len(result.data) == 1


async def test_calculate_refund_eligible_for_succeeded_payment(committed_session: AsyncSession) -> None:
    org, _free, pro = await create_org_and_plan(committed_session)
    customer = await create_customer_with_account(committed_session, org, pro)
    subscription = customer.subscriptions[0]
    payment = await create_payment(
        committed_session, customer, subscription.id, 49, PaymentStatus.SUCCEEDED, _PERIOD
    )
    await committed_session.commit()
    await _register(committed_session, org)

    result = await billing.calculate_refund(payment.id)

    assert result.success is True
    assert result.data.is_eligible is True
    assert result.data.refundable_amount == 49.0


async def test_create_refund_request_happy_path(committed_session: AsyncSession) -> None:
    org, _free, pro = await create_org_and_plan(committed_session)
    customer = await create_customer_with_account(committed_session, org, pro)
    subscription = customer.subscriptions[0]
    payment = await create_payment(
        committed_session, customer, subscription.id, 49, PaymentStatus.SUCCEEDED, _PERIOD
    )
    await committed_session.commit()
    await _register(committed_session, org)

    result = await billing.create_refund_request(payment.id, reason="duplicate charge")

    assert result.success is True
    assert result.data.status == "pending_approval"


async def test_create_refund_request_invalid_state_for_failed_payment(
    committed_session: AsyncSession,
) -> None:
    org, _free, pro = await create_org_and_plan(committed_session)
    customer = await create_customer_with_account(committed_session, org, pro)
    subscription = customer.subscriptions[0]
    payment = await create_payment(
        committed_session, customer, subscription.id, 49, PaymentStatus.FAILED, _PERIOD
    )
    await committed_session.commit()
    await _register(committed_session, org)

    result = await billing.create_refund_request(payment.id, reason="n/a")

    assert result.success is False
    assert "status=failed" in result.error


async def test_get_billing_policy_happy_path(committed_session: AsyncSession) -> None:
    committed_session.add(
        SupportPolicy(
            policy_key="refund_rules_test",
            title="Refund Rules",
            description="Full refunds within 30 days.",
            rules={"window_days": 30},
        )
    )
    await committed_session.commit()

    result = await billing.get_billing_policy("refund_rules_test")

    assert result.success is True
    assert result.data.title == "Refund Rules"


async def test_get_billing_policy_not_found(committed_session: AsyncSession) -> None:
    result = await billing.get_billing_policy("does_not_exist_policy")

    assert result.success is False

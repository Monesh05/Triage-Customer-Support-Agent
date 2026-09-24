# tests/test_api_refunds.py
# Purpose: Integration tests for POST /api/v1/refunds/request, covering the duplicate-
#          payment happy path, an invalid-state (non-succeeded payment) rejection, and a
#          not-found response for an unknown payment id.
# Author: CloudDesk Team
# Date: 2026-09-21

from datetime import datetime, timezone

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PaymentStatus
from app.models.subscription import Subscription
from tests.conftest import auth_headers, new_id, staff_auth_headers
from tests.factories import create_customer_with_account, create_org_and_plan, create_payment


async def test_request_refund_succeeds_for_succeeded_payment(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    org, _free, pro = await create_org_and_plan(db_session)
    customer = await create_customer_with_account(db_session, org, pro)
    result = await db_session.execute(select(Subscription).where(Subscription.customer_id == customer.id))
    subscription = result.scalar_one()
    payment = await create_payment(
        db_session, customer, subscription.id, 49, PaymentStatus.SUCCEEDED,
        datetime(2026, 9, 1, tzinfo=timezone.utc),
    )

    response = await client.post(
        "/api/v1/refunds/request",
        json={"payment_id": str(payment.id), "reason": "duplicate charge"},
        headers=auth_headers(customer.id),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending_approval"
    assert body["amount"] == 49.0


async def test_request_refund_returns_409_for_failed_payment(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    org, _free, pro = await create_org_and_plan(db_session)
    customer = await create_customer_with_account(db_session, org, pro)
    result = await db_session.execute(select(Subscription).where(Subscription.customer_id == customer.id))
    subscription = result.scalar_one()
    payment = await create_payment(
        db_session, customer, subscription.id, 49, PaymentStatus.FAILED,
        datetime(2026, 9, 1, tzinfo=timezone.utc),
    )

    response = await client.post(
        "/api/v1/refunds/request",
        json={"payment_id": str(payment.id), "reason": "n/a"},
        headers=auth_headers(customer.id),
    )

    assert response.status_code == 409


async def test_request_refund_returns_404_for_unknown_payment(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/refunds/request", json={"payment_id": str(new_id()), "reason": "n/a"}, headers=staff_auth_headers()
    )

    assert response.status_code == 404


async def test_request_refund_returns_403_for_a_different_customers_token(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    org, _free, pro = await create_org_and_plan(db_session)
    customer = await create_customer_with_account(db_session, org, pro)
    result = await db_session.execute(select(Subscription).where(Subscription.customer_id == customer.id))
    subscription = result.scalar_one()
    payment = await create_payment(
        db_session, customer, subscription.id, 49, PaymentStatus.SUCCEEDED,
        datetime(2026, 9, 1, tzinfo=timezone.utc),
    )

    response = await client.post(
        "/api/v1/refunds/request",
        json={"payment_id": str(payment.id), "reason": "not mine"},
        headers=auth_headers(new_id()),
    )

    assert response.status_code == 403

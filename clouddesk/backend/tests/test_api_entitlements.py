# tests/test_api_entitlements.py
# Purpose: Integration test for POST /api/v1/entitlements/refresh, covering the
#          stale-Pro-subscription-with-Free-entitlement scenario from spec section 6/11.
# Author: CloudDesk Team
# Date: 2026-09-21

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import auth_headers
from tests.factories import create_customer_with_account, create_org_and_plan


async def test_refresh_entitlement_endpoint_resolves_stale_mismatch(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    org, free, pro = await create_org_and_plan(db_session)
    customer = await create_customer_with_account(db_session, org, pro)
    subscription = customer.subscriptions[0]
    subscription.entitlement.granted_plan_id = free.id
    subscription.entitlement.granted_api_rate_limit = free.api_rate_limit
    await db_session.flush()

    response = await client.post(
        "/api/v1/entitlements/refresh",
        json={"customer_id": str(customer.id), "reason": "customer reported 403s"},
        headers=auth_headers(customer.id),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["was_stale"] is True
    assert body["entitlement"]["granted_plan_id"] == str(pro.id)

# tests/test_api_customers.py
# Purpose: Integration tests for GET /api/v1/customers/{customer_id}.
# Author: CloudDesk Team
# Date: 2026-09-21

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import new_id
from tests.factories import create_customer_with_account, create_org_and_plan


async def test_get_customer_returns_200_for_existing_customer(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    org, _free, pro = await create_org_and_plan(db_session)
    customer = await create_customer_with_account(db_session, org, pro)

    response = await client.get(f"/api/v1/customers/{customer.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(customer.id)
    assert body["status"] == "active"


async def test_get_customer_returns_404_for_unknown_customer(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/customers/{new_id()}")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

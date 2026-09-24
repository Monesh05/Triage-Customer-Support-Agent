# tests/test_api_customers.py
# Purpose: Integration tests for GET /api/v1/customers/{customer_id} and (Phase 9, spec
#          sections 25/26) GET /api/v1/customers/{customer_id}/tickets.
# Author: CloudDesk Team
# Date: 2026-09-24

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TicketPriority
from app.services import ticket_service
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


async def test_get_customer_tickets_returns_most_recent_first(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    org, _free, pro = await create_org_and_plan(db_session)
    customer = await create_customer_with_account(db_session, org, pro)
    first = await ticket_service.create_ticket(
        db_session, customer.id, "First issue", "Description one", TicketPriority.LOW, "test:actor",
    )
    second = await ticket_service.create_ticket(
        db_session, customer.id, "Second issue", "Description two", TicketPriority.HIGH, "test:actor",
    )

    response = await client.get(f"/api/v1/customers/{customer.id}/tickets")

    assert response.status_code == 200
    body = response.json()
    ids = [t["id"] for t in body]
    assert ids.index(str(second.id)) < ids.index(str(first.id))


async def test_get_customer_tickets_returns_404_for_unknown_customer(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/customers/{new_id()}/tickets")

    assert response.status_code == 404

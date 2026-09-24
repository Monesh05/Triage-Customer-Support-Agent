# tests/test_api_tickets.py
# Purpose: Integration tests for POST /api/v1/tickets and GET /api/v1/tickets/{ticket_id}.
# Author: CloudDesk Team
# Date: 2026-09-21

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import auth_headers, new_id, staff_auth_headers
from tests.factories import create_customer_with_account, create_org_and_plan


async def test_create_and_fetch_ticket(client: AsyncClient, db_session: AsyncSession) -> None:
    org, _free, pro = await create_org_and_plan(db_session)
    customer = await create_customer_with_account(db_session, org, pro)

    create_response = await client.post(
        "/api/v1/tickets",
        json={
            "customer_id": str(customer.id),
            "subject": "Charged twice",
            "description": "I see two $49 charges for September.",
            "priority": "high",
        },
        headers=auth_headers(customer.id),
    )
    assert create_response.status_code == 201
    ticket_id = create_response.json()["id"]

    get_response = await client.get(f"/api/v1/tickets/{ticket_id}", headers=staff_auth_headers())

    assert get_response.status_code == 200
    body = get_response.json()
    assert body["subject"] == "Charged twice"
    assert body["status"] == "open"
    assert body["priority"] == "high"


async def test_create_ticket_returns_404_for_unknown_customer(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/tickets",
        json={"customer_id": str(new_id()), "subject": "x", "description": "y"},
        headers=staff_auth_headers(),
    )

    assert response.status_code == 404


async def test_get_ticket_returns_404_for_unknown_ticket(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/tickets/{new_id()}", headers=staff_auth_headers())

    assert response.status_code == 404


async def test_read_all_tickets_requires_staff_role(client: AsyncClient, db_session: AsyncSession) -> None:
    org, _free, pro = await create_org_and_plan(db_session)
    customer = await create_customer_with_account(db_session, org, pro)

    response = await client.get("/api/v1/tickets", headers=auth_headers(customer.id))

    assert response.status_code == 403

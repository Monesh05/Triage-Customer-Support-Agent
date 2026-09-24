# tests/test_api_accounts.py
# Purpose: Integration tests for GET/POST account endpoints, including the unlock workflow.
# Author: CloudDesk Team
# Date: 2026-09-21

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AccountStatus
from tests.conftest import auth_headers
from tests.factories import create_customer_with_account, create_org_and_plan


async def test_get_account_returns_locked_status(client: AsyncClient, db_session: AsyncSession) -> None:
    org, _free, pro = await create_org_and_plan(db_session)
    customer = await create_customer_with_account(
        db_session, org, pro, account_status=AccountStatus.LOCKED, failed_login_attempts=6
    )

    response = await client.get(f"/api/v1/accounts/{customer.id}", headers=auth_headers(customer.id))

    assert response.status_code == 200
    assert response.json()["status"] == "locked"


async def test_unlock_account_endpoint_succeeds_for_locked_account(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    org, _free, pro = await create_org_and_plan(db_session)
    customer = await create_customer_with_account(
        db_session, org, pro, account_status=AccountStatus.LOCKED, failed_login_attempts=6
    )

    response = await client.post(
        "/api/v1/accounts/unlock",
        json={"customer_id": str(customer.id), "reason": "identity verified"},
        headers=auth_headers(customer.id),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "active"
    assert body["failed_login_attempts"] == 0


async def test_unlock_account_endpoint_returns_409_when_not_locked(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    org, _free, pro = await create_org_and_plan(db_session)
    customer = await create_customer_with_account(db_session, org, pro, account_status=AccountStatus.ACTIVE)

    response = await client.post(
        "/api/v1/accounts/unlock",
        json={"customer_id": str(customer.id), "reason": "n/a"},
        headers=auth_headers(customer.id),
    )

    assert response.status_code == 409

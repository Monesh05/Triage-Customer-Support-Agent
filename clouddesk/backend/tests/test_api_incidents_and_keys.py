# tests/test_api_incidents_and_keys.py
# Purpose: Integration tests for GET /api/v1/incidents and GET /api/v1/api-keys/{customer_id},
#          specifically asserting that API key responses never leak `key_hash`.
# Author: CloudDesk Team
# Date: 2026-09-21

from datetime import datetime, timezone

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import ApiKey
from app.models.enums import IncidentSeverity, IncidentStatus
from app.models.incident import ServiceIncident
from tests.conftest import auth_headers
from tests.factories import create_customer_with_account, create_org_and_plan


async def test_list_incidents_returns_seeded_incident(client: AsyncClient, db_session: AsyncSession) -> None:
    db_session.add(
        ServiceIncident(
            service_name="API",
            status=IncidentStatus.MONITORING,
            severity=IncidentSeverity.HIGH,
            started_at=datetime(2026, 9, 20, tzinfo=timezone.utc),
            description="Elevated error rates.",
        )
    )
    await db_session.flush()

    response = await client.get("/api/v1/incidents")

    assert response.status_code == 200
    services = [incident["service_name"] for incident in response.json()]
    assert "API" in services


async def test_api_key_response_never_includes_key_hash(client: AsyncClient, db_session: AsyncSession) -> None:
    org, _free, pro = await create_org_and_plan(db_session)
    customer = await create_customer_with_account(db_session, org, pro)

    db_session.add(ApiKey(customer=customer, key_hash="sha256:should-never-appear", rate_limit=1000))
    await db_session.flush()

    response = await client.get(f"/api/v1/api-keys/{customer.id}", headers=auth_headers(customer.id))

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert "key_hash" not in body[0]
    assert "should-never-appear" not in response.text

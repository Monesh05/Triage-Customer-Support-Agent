# tests/test_api_traces.py
# Purpose: Integration tests for the Phase 7 Agent Observability read API (spec sections 24, 26):
#          GET /api/v1/tickets/{ticket_id}/trace and GET /api/v1/traces/{run_id}, including 404s
#          for an unknown ticket/run id. Uses the `client`/`db_session` fixtures (real Postgres,
#          rolled back per test), same pattern as every other API test in this suite.
# Author: CloudDesk Team
# Date: 2026-09-24

import uuid
from datetime import datetime, timedelta, timezone

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AgentRunStatus, TicketPriority
from app.services import observability_service, ticket_service
from tests.conftest import new_id
from tests.factories import create_customer_with_account, create_org_and_plan

_START = datetime(2026, 9, 24, 12, 0, 0, tzinfo=timezone.utc)


async def _make_ticket(session: AsyncSession) -> uuid.UUID:
    org, _free, pro = await create_org_and_plan(session)
    customer = await create_customer_with_account(session, org, pro)
    ticket = await ticket_service.create_ticket(
        session, customer.id, "API trace test", "Description", TicketPriority.MEDIUM, "test:actor",
    )
    return ticket.id


async def _make_agent_run(session: AsyncSession, ticket_id: uuid.UUID, agent_name: str, offset: int):
    start = _START + timedelta(seconds=offset)
    return await observability_service.create_agent_run(
        session,
        ticket_id=ticket_id,
        thread_id="thread-api-test",
        agent_name=agent_name,
        start_time=start,
        end_time=start + timedelta(milliseconds=200),
        duration_ms=200,
        status=AgentRunStatus.SUCCESS,
        input_summary="hello",
        output_summary="ok",
        tool_calls=[],
        tool_results=[],
        error=None,
        iteration=None,
    )


async def test_read_ticket_trace_returns_ordered_runs(client: AsyncClient, db_session: AsyncSession) -> None:
    ticket_id = await _make_ticket(db_session)
    await _make_agent_run(db_session, ticket_id, "triage", 0)
    await _make_agent_run(db_session, ticket_id, "product", 1)

    response = await client.get(f"/api/v1/tickets/{ticket_id}/trace")

    assert response.status_code == 200
    body = response.json()
    assert body["ticket_id"] == str(ticket_id)
    assert [run["agent_name"] for run in body["runs"]] == ["triage", "product"]
    assert body["runs"][0]["run_id"]
    assert body["runs"][0]["status"] == "success"


async def test_read_ticket_trace_empty_for_ticket_with_no_runs(client: AsyncClient, db_session: AsyncSession) -> None:
    ticket_id = await _make_ticket(db_session)

    response = await client.get(f"/api/v1/tickets/{ticket_id}/trace")

    assert response.status_code == 200
    assert response.json()["runs"] == []


async def test_read_ticket_trace_404_for_unknown_ticket(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/tickets/{new_id()}/trace")

    assert response.status_code == 404


async def test_read_agent_run_returns_single_record(client: AsyncClient, db_session: AsyncSession) -> None:
    ticket_id = await _make_ticket(db_session)
    agent_run = await _make_agent_run(db_session, ticket_id, "billing", 0)

    response = await client.get(f"/api/v1/traces/{agent_run.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == str(agent_run.id)
    assert body["agent_name"] == "billing"


async def test_read_agent_run_404_for_unknown_run_id(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/traces/{new_id()}")

    assert response.status_code == 404

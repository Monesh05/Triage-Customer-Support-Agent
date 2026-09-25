# tests/test_api_ticket_close.py
# Purpose: Integration tests for the post-launch (2026-09-25) customer-facing ticket detail
#          endpoints: GET /api/v1/tickets/{id}/summary and POST /api/v1/tickets/{id}/close.
#          Covers: a customer closing their own ticket, rejecting a second close (409), rejecting
#          another customer's close attempt (403), staff being able to close on a customer's
#          behalf, and the summary endpoint returning a customer-safe view (no raw agent
#          tool_calls/tool_results) that reflects the ticket's real resolution/escalation outcome.
# Author: CloudDesk Team
# Date: 2026-09-25

from datetime import datetime, timezone

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import ConversationRecord
from app.models.customer import Customer
from app.models.enums import TicketPriority
from app.models.ticket import SupportTicket
from tests.conftest import auth_headers, new_id, staff_auth_headers
from tests.factories import create_customer_with_account, create_org_and_plan


async def _create_ticket(session: AsyncSession, customer: Customer) -> SupportTicket:
    ticket = SupportTicket(
        customer_id=customer.id,
        subject="Charged twice",
        description="I see two $49 charges for September.",
        priority=TicketPriority.HIGH,
    )
    session.add(ticket)
    await session.commit()
    await session.refresh(ticket)
    return ticket


async def test_customer_can_close_own_ticket(client: AsyncClient, committed_session: AsyncSession) -> None:
    org, _free, pro = await create_org_and_plan(committed_session)
    customer = await create_customer_with_account(committed_session, org, pro)
    ticket = await _create_ticket(committed_session, customer)

    response = await client.post(f"/api/v1/tickets/{ticket.id}/close", headers=auth_headers(customer.id))

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "closed"
    assert body["id"] == str(ticket.id)


async def test_closing_an_already_closed_ticket_is_rejected(
    client: AsyncClient, committed_session: AsyncSession
) -> None:
    org, _free, pro = await create_org_and_plan(committed_session)
    customer = await create_customer_with_account(committed_session, org, pro)
    ticket = await _create_ticket(committed_session, customer)

    first = await client.post(f"/api/v1/tickets/{ticket.id}/close", headers=auth_headers(customer.id))
    assert first.status_code == 200

    second = await client.post(f"/api/v1/tickets/{ticket.id}/close", headers=auth_headers(customer.id))
    assert second.status_code == 409


async def test_customer_cannot_close_another_customers_ticket(
    client: AsyncClient, committed_session: AsyncSession
) -> None:
    org, _free, pro = await create_org_and_plan(committed_session)
    owner = await create_customer_with_account(committed_session, org, pro)
    other = await create_customer_with_account(committed_session, org, pro)
    ticket = await _create_ticket(committed_session, owner)

    response = await client.post(f"/api/v1/tickets/{ticket.id}/close", headers=auth_headers(other.id))

    assert response.status_code == 403


async def test_staff_can_close_a_customers_ticket(client: AsyncClient, committed_session: AsyncSession) -> None:
    org, _free, pro = await create_org_and_plan(committed_session)
    customer = await create_customer_with_account(committed_session, org, pro)
    ticket = await _create_ticket(committed_session, customer)

    response = await client.post(f"/api/v1/tickets/{ticket.id}/close", headers=staff_auth_headers())

    assert response.status_code == 200
    assert response.json()["status"] == "closed"


async def test_close_ticket_returns_404_for_unknown_ticket(client: AsyncClient) -> None:
    response = await client.post(f"/api/v1/tickets/{new_id()}/close", headers=staff_auth_headers())

    assert response.status_code == 404


async def test_customer_can_read_own_ticket_but_not_anothers(
    client: AsyncClient, committed_session: AsyncSession
) -> None:
    org, _free, pro = await create_org_and_plan(committed_session)
    owner = await create_customer_with_account(committed_session, org, pro)
    other = await create_customer_with_account(committed_session, org, pro)
    ticket = await _create_ticket(committed_session, owner)

    own_response = await client.get(f"/api/v1/tickets/{ticket.id}", headers=auth_headers(owner.id))
    assert own_response.status_code == 200

    other_response = await client.get(f"/api/v1/tickets/{ticket.id}", headers=auth_headers(other.id))
    assert other_response.status_code == 403


async def test_ticket_summary_reflects_escalation_and_hides_agent_internals(
    client: AsyncClient, committed_session: AsyncSession
) -> None:
    org, _free, pro = await create_org_and_plan(committed_session)
    customer = await create_customer_with_account(committed_session, org, pro)
    ticket = await _create_ticket(committed_session, customer)

    escalation_message = (
        "Your issue has been escalated to a human specialist who will review the full details of "
        "your case and follow up with you directly."
    )
    conversation = ConversationRecord(
        thread_id=f"thread-{ticket.id}",
        customer_id=str(customer.id),
        ticket_id=str(ticket.id),
        status="escalated",
        final_response=escalation_message,
        started_at=datetime.now(timezone.utc),
    )
    committed_session.add(conversation)
    await committed_session.commit()

    response = await client.get(f"/api/v1/tickets/{ticket.id}/summary", headers=auth_headers(customer.id))

    assert response.status_code == 200
    body = response.json()
    assert body["ticket_id"] == str(ticket.id)
    assert body["escalated"] is True
    assert body["resolution_message"] == escalation_message
    assert "tool_calls" not in body
    assert "tool_results" not in body


async def test_ticket_summary_with_no_conversation_yet(client: AsyncClient, committed_session: AsyncSession) -> None:
    org, _free, pro = await create_org_and_plan(committed_session)
    customer = await create_customer_with_account(committed_session, org, pro)
    ticket = await _create_ticket(committed_session, customer)

    response = await client.get(f"/api/v1/tickets/{ticket.id}/summary", headers=auth_headers(customer.id))

    assert response.status_code == 200
    body = response.json()
    assert body["escalated"] is False
    assert body["resolution_message"] is None

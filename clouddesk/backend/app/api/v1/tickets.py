# app/api/v1/tickets.py
# Purpose: REST endpoints for retrieving and creating support tickets (spec section 7), plus
#          (Phase 9, spec section 26) a cross-customer ticket list for the Support Console. Phase
#          10 (spec section 27): the cross-customer list is internal Support Console tooling and
#          requires staff. Creating a ticket, or reading a single ticket by id, requires the
#          requester to be staff OR the ticket's own customer (`require_customer_access`) —
#          reading a single ticket used to be staff-only, but the customer portal's new ticket
#          detail page (post-launch, 2026-09-25) needs a customer to read their OWN ticket, so
#          that gap was closed here rather than left staff-only. Post-launch (2026-09-25) also
#          adds GET .../{id}/summary (a customer-safe outcome view, distinct from the staff-only
#          raw Agent Observability trace at GET .../{id}/trace — see app.api.v1.traces) and
#          POST .../{id}/close (a customer closing their own ticket).
# Author: CloudDesk Team
# Date: 2026-09-25

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_claims, require_customer_access, require_staff_role
from app.core.security import TokenClaims
from app.database.session import get_db_session
from app.schemas.ticket import SupportTicketCreate, SupportTicketResponse, TicketSummaryResponse
from app.services import conversation_service
from app.services.ticket_service import close_ticket, create_ticket, get_ticket_by_id, list_all_tickets

router = APIRouter(prefix="/tickets", tags=["tickets"])

_TICKET_CREATE_ACTOR = "api:tickets.create"


@router.get("", response_model=list[SupportTicketResponse], dependencies=[Depends(require_staff_role)])
async def read_all_tickets(session: AsyncSession = Depends(get_db_session)) -> list[SupportTicketResponse]:
    """List support tickets across all customers, most recent first (Support Console Tickets
    list, spec section 26). Staff-only: this is a cross-customer view."""
    tickets = await list_all_tickets(session)
    return [SupportTicketResponse.model_validate(t) for t in tickets]


@router.get("/{ticket_id}", response_model=SupportTicketResponse)
async def read_ticket(
    ticket_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    claims: TokenClaims = Depends(get_current_claims),
) -> SupportTicketResponse:
    """Return a single support ticket by id. Staff may read any ticket; a customer may only read
    their own (403 otherwise, via `require_customer_access` — org policy A01: never trust a
    client-supplied id, so ownership is checked against the ticket's OWN `customer_id`, not
    anything the caller supplied)."""
    ticket = await get_ticket_by_id(session, ticket_id)
    require_customer_access(ticket.customer_id, claims)
    return SupportTicketResponse.model_validate(ticket)


@router.get("/{ticket_id}/summary", response_model=TicketSummaryResponse)
async def read_ticket_summary(
    ticket_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    claims: TokenClaims = Depends(get_current_claims),
) -> TicketSummaryResponse:
    """A customer-safe outcome summary for one ticket: original request, status, whether it was
    escalated, and the same sanitized resolution text the chat itself showed (spec section 25's
    no-chain-of-thought rule) — never the raw specialist tool_calls/tool_results/reasoning the
    staff-only GET .../{id}/trace exposes. Staff may read any ticket's summary; a customer may
    only read their own.
    """
    ticket = await get_ticket_by_id(session, ticket_id)
    require_customer_access(ticket.customer_id, claims)
    conversation = await conversation_service.get_latest_conversation_for_ticket(ticket_id)
    return TicketSummaryResponse.from_ticket_and_conversation(ticket, conversation)


@router.post("/{ticket_id}/close", response_model=SupportTicketResponse)
async def close_ticket_endpoint(
    ticket_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    claims: TokenClaims = Depends(get_current_claims),
) -> SupportTicketResponse:
    """Close a ticket at its own customer's request (or staff acting on their behalf). 404s if the
    ticket does not exist, 403s if the caller does not own it, 409s (via the app-wide
    `InvalidStateError` handler) if it is already closed.
    """
    ticket = await get_ticket_by_id(session, ticket_id)
    require_customer_access(ticket.customer_id, claims)
    closed_ticket = await close_ticket(session, ticket_id)
    return SupportTicketResponse.model_validate(closed_ticket)


@router.post("", response_model=SupportTicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket_endpoint(
    payload: SupportTicketCreate,
    session: AsyncSession = Depends(get_db_session),
    claims: TokenClaims = Depends(get_current_claims),
) -> SupportTicketResponse:
    """Create a new support ticket for a customer."""
    require_customer_access(payload.customer_id, claims)
    ticket = await create_ticket(
        session,
        customer_id=payload.customer_id,
        subject=payload.subject,
        description=payload.description,
        priority=payload.priority,
        actor=_TICKET_CREATE_ACTOR,
    )
    return SupportTicketResponse.model_validate(ticket)

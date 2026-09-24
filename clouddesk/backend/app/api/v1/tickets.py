# app/api/v1/tickets.py
# Purpose: REST endpoints for retrieving and creating support tickets (spec section 7), plus
#          (Phase 9, spec section 26) a cross-customer ticket list for the Support Console. Phase
#          10 (spec section 27): reading a ticket by id, or the cross-customer list, is internal
#          Support Console tooling (confirmed against the frontend: clouddesk/frontend/src/lib/
#          api/tickets.ts only calls these from support-console pages) so both require staff.
#          Creating a ticket requires the requester to be staff or the ticket's own customer.
# Author: CloudDesk Team
# Date: 2026-09-24

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_claims, require_customer_access, require_staff_role
from app.core.security import TokenClaims
from app.database.session import get_db_session
from app.schemas.ticket import SupportTicketCreate, SupportTicketResponse
from app.services.ticket_service import create_ticket, get_ticket_by_id, list_all_tickets

router = APIRouter(prefix="/tickets", tags=["tickets"])

_TICKET_CREATE_ACTOR = "api:tickets.create"


@router.get("", response_model=list[SupportTicketResponse], dependencies=[Depends(require_staff_role)])
async def read_all_tickets(session: AsyncSession = Depends(get_db_session)) -> list[SupportTicketResponse]:
    """List support tickets across all customers, most recent first (Support Console Tickets
    list, spec section 26). Staff-only: this is a cross-customer view."""
    tickets = await list_all_tickets(session)
    return [SupportTicketResponse.model_validate(t) for t in tickets]


@router.get("/{ticket_id}", response_model=SupportTicketResponse, dependencies=[Depends(require_staff_role)])
async def read_ticket(
    ticket_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)
) -> SupportTicketResponse:
    """Return a single support ticket by id. Staff-only (Support Console tooling)."""
    ticket = await get_ticket_by_id(session, ticket_id)
    return SupportTicketResponse.model_validate(ticket)


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

# app/api/v1/tickets.py
# Purpose: REST endpoints for retrieving and creating support tickets (spec section 7), plus
#          (Phase 9, spec section 26) a cross-customer ticket list for the Support Console.
# Author: CloudDesk Team
# Date: 2026-09-24

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.schemas.ticket import SupportTicketCreate, SupportTicketResponse
from app.services.ticket_service import create_ticket, get_ticket_by_id, list_all_tickets

router = APIRouter(prefix="/tickets", tags=["tickets"])

_TICKET_CREATE_ACTOR = "api:tickets.create"


@router.get("", response_model=list[SupportTicketResponse])
async def read_all_tickets(session: AsyncSession = Depends(get_db_session)) -> list[SupportTicketResponse]:
    """List support tickets across all customers, most recent first (Support Console Tickets
    list, spec section 26)."""
    tickets = await list_all_tickets(session)
    return [SupportTicketResponse.model_validate(t) for t in tickets]


@router.get("/{ticket_id}", response_model=SupportTicketResponse)
async def read_ticket(
    ticket_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)
) -> SupportTicketResponse:
    """Return a single support ticket by id."""
    ticket = await get_ticket_by_id(session, ticket_id)
    return SupportTicketResponse.model_validate(ticket)


@router.post("", response_model=SupportTicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket_endpoint(
    payload: SupportTicketCreate, session: AsyncSession = Depends(get_db_session)
) -> SupportTicketResponse:
    """Create a new support ticket for a customer."""
    ticket = await create_ticket(
        session,
        customer_id=payload.customer_id,
        subject=payload.subject,
        description=payload.description,
        priority=payload.priority,
        actor=_TICKET_CREATE_ACTOR,
    )
    return SupportTicketResponse.model_validate(ticket)

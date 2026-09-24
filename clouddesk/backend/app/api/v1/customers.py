# app/api/v1/customers.py
# Purpose: REST endpoints for retrieving customer records (spec section 7), plus (Phase 9,
#          spec sections 25/26) a customer's own support-ticket history for a frontend support-
#          history view / the Support Console's per-customer ticket list. Phase 10 (spec
#          section 27): the requesting identity must be either staff or this exact customer —
#          `customer_id` in the path is only ever used to look the record up, never trusted for
#          authorization by itself (org policy A01, IDOR prevention).
# Author: CloudDesk Team
# Date: 2026-09-24

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_claims, require_customer_access
from app.core.security import TokenClaims
from app.database.session import get_db_session
from app.schemas.customer import CustomerResponse
from app.schemas.ticket import SupportTicketResponse
from app.services.customer_service import get_customer_by_id
from app.services.ticket_service import list_tickets_for_customer

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("/{customer_id}", response_model=CustomerResponse)
async def read_customer(
    customer_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    claims: TokenClaims = Depends(get_current_claims),
) -> CustomerResponse:
    """Return a single customer by id. Staff may look up any customer; a customer token may only
    look up itself."""
    require_customer_access(customer_id, claims)
    customer = await get_customer_by_id(session, customer_id)
    return CustomerResponse.model_validate(customer)


@router.get("/{customer_id}/tickets", response_model=list[SupportTicketResponse])
async def read_customer_tickets(
    customer_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    claims: TokenClaims = Depends(get_current_claims),
) -> list[SupportTicketResponse]:
    """List a customer's support tickets, most recent first. 404s if the customer does not exist."""
    require_customer_access(customer_id, claims)
    tickets = await list_tickets_for_customer(session, customer_id)
    return [SupportTicketResponse.model_validate(t) for t in tickets]

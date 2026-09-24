# app/api/v1/invoices.py
# Purpose: REST endpoint for retrieving a customer's invoices (spec section 7).
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_claims, require_customer_access
from app.core.security import TokenClaims
from app.database.session import get_db_session
from app.schemas.invoice import InvoiceResponse
from app.services.invoice_service import get_invoices_by_customer

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("/{customer_id}", response_model=list[InvoiceResponse])
async def read_invoices(
    customer_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    claims: TokenClaims = Depends(get_current_claims),
) -> list[InvoiceResponse]:
    """Return all invoices for a customer, most recently issued first."""
    require_customer_access(customer_id, claims)
    invoices = await get_invoices_by_customer(session, customer_id)
    return [InvoiceResponse.model_validate(i) for i in invoices]

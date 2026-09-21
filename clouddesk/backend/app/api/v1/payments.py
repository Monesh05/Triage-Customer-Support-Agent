# app/api/v1/payments.py
# Purpose: REST endpoint for retrieving a customer's payments (spec section 7).
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.schemas.payment import PaymentResponse
from app.services.payment_service import get_payments_by_customer

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/{customer_id}", response_model=list[PaymentResponse])
async def read_payments(
    customer_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)
) -> list[PaymentResponse]:
    """Return all payments for a customer, most recent first."""
    payments = await get_payments_by_customer(session, customer_id)
    return [PaymentResponse.model_validate(p) for p in payments]

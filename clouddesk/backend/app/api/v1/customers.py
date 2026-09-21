# app/api/v1/customers.py
# Purpose: REST endpoints for retrieving customer records (spec section 7).
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.schemas.customer import CustomerResponse
from app.services.customer_service import get_customer_by_id

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("/{customer_id}", response_model=CustomerResponse)
async def read_customer(
    customer_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)
) -> CustomerResponse:
    """Return a single customer by id."""
    customer = await get_customer_by_id(session, customer_id)
    return CustomerResponse.model_validate(customer)

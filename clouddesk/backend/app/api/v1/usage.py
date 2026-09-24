# app/api/v1/usage.py
# Purpose: REST endpoint for retrieving a customer's API usage records (spec section 7).
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_claims, require_customer_access
from app.core.security import TokenClaims
from app.database.session import get_db_session
from app.schemas.usage import UsageRecordResponse
from app.services.usage_service import get_usage_by_customer

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/{customer_id}", response_model=list[UsageRecordResponse])
async def read_usage(
    customer_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    claims: TokenClaims = Depends(get_current_claims),
) -> list[UsageRecordResponse]:
    """Return all usage records for a customer, most recent period first."""
    require_customer_access(customer_id, claims)
    records = await get_usage_by_customer(session, customer_id)
    return [UsageRecordResponse.model_validate(r) for r in records]

# app/api/v1/subscriptions.py
# Purpose: REST endpoint for retrieving a customer's subscriptions (spec section 7).
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_claims, require_customer_access
from app.core.security import TokenClaims
from app.database.session import get_db_session
from app.schemas.subscription import SubscriptionResponse
from app.services.subscription_service import get_subscriptions_by_customer

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("/{customer_id}", response_model=list[SubscriptionResponse])
async def read_subscriptions(
    customer_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    claims: TokenClaims = Depends(get_current_claims),
) -> list[SubscriptionResponse]:
    """Return all subscriptions for a customer, including plan and entitlement details."""
    require_customer_access(customer_id, claims)
    subscriptions = await get_subscriptions_by_customer(session, customer_id)
    return [SubscriptionResponse.model_validate(s) for s in subscriptions]

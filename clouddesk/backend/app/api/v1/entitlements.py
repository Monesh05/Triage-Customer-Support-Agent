# app/api/v1/entitlements.py
# Purpose: REST endpoint to refresh a customer's subscription entitlement so it matches
#          their current plan (spec section 7), resolving stale-entitlement scenarios.
# Author: CloudDesk Team
# Date: 2026-09-21

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_claims, require_customer_access
from app.core.security import TokenClaims
from app.database.session import get_db_session
from app.schemas.subscription import (
    EntitlementRefreshRequest,
    EntitlementRefreshResponse,
    EntitlementResponse,
)
from app.services.subscription_service import refresh_entitlement

router = APIRouter(prefix="/entitlements", tags=["entitlements"])

_ENTITLEMENT_REFRESH_ACTOR = "api:entitlements.refresh"


@router.post("/refresh", response_model=EntitlementRefreshResponse)
async def refresh_entitlement_endpoint(
    payload: EntitlementRefreshRequest,
    session: AsyncSession = Depends(get_db_session),
    claims: TokenClaims = Depends(get_current_claims),
) -> EntitlementRefreshResponse:
    """Re-sync a customer's entitlement to match their current subscription plan."""
    require_customer_access(payload.customer_id, claims)
    subscription, was_stale = await refresh_entitlement(
        session,
        customer_id=payload.customer_id,
        reason=payload.reason,
        actor=_ENTITLEMENT_REFRESH_ACTOR,
    )
    message = (
        "Entitlement was stale and has been refreshed to match the current plan."
        if was_stale
        else "Entitlement was already in sync with the current plan."
    )
    return EntitlementRefreshResponse(
        subscription_id=subscription.id,
        was_stale=was_stale,
        entitlement=EntitlementResponse.model_validate(subscription.entitlement),
        message=message,
    )

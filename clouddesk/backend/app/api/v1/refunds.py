# app/api/v1/refunds.py
# Purpose: REST endpoint for requesting a refund (spec section 7). Creates a pending-approval
#          refund request record; it never marks a payment as refunded (human approval
#          required per spec section 22). Phase 10 (spec section 27): the requester must be staff
#          or the customer who actually owns the payment being disputed — the payment is looked
#          up first specifically so this check has a real customer id to compare against, not a
#          client-supplied one.
# Author: CloudDesk Team
# Date: 2026-09-21

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_claims, require_customer_access
from app.core.security import TokenClaims
from app.database.session import get_db_session
from app.schemas.payment import RefundRequestCreate, RefundRequestResponse
from app.services.payment_service import create_refund_request, get_payment_by_id

router = APIRouter(prefix="/refunds", tags=["refunds"])

_REFUND_REQUEST_ACTOR = "api:refunds.request"


@router.post("/request", response_model=RefundRequestResponse, status_code=status.HTTP_201_CREATED)
async def request_refund(
    payload: RefundRequestCreate,
    session: AsyncSession = Depends(get_db_session),
    claims: TokenClaims = Depends(get_current_claims),
) -> RefundRequestResponse:
    """Create a pending-approval refund request for a succeeded payment."""
    payment = await get_payment_by_id(session, payload.payment_id)
    require_customer_access(payment.customer_id, claims)
    refund_request = await create_refund_request(
        session,
        payment_id=payload.payment_id,
        reason=payload.reason,
        actor=_REFUND_REQUEST_ACTOR,
    )
    return RefundRequestResponse.model_validate(refund_request)

# app/api/v1/accounts.py
# Purpose: REST endpoints for account retrieval and unlocking (spec section 7). Phase 10 (spec
#          section 27): both require the requester to be staff or the account's own customer —
#          unlocking is normally agent/staff-initiated, but a customer may also confirm their own
#          unlock, so this is not staff-only.
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_claims, require_customer_access
from app.core.security import TokenClaims
from app.database.session import get_db_session
from app.schemas.account import AccountResponse, AccountUnlockRequest, AccountUnlockResponse
from app.services.account_service import get_account_by_customer_id, unlock_account

router = APIRouter(prefix="/accounts", tags=["accounts"])

_UNLOCK_ACTOR = "api:accounts.unlock"


@router.get("/{customer_id}", response_model=AccountResponse)
async def read_account(
    customer_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    claims: TokenClaims = Depends(get_current_claims),
) -> AccountResponse:
    """Return the account/security state for a customer."""
    require_customer_access(customer_id, claims)
    account = await get_account_by_customer_id(session, customer_id)
    return AccountResponse.model_validate(account)


@router.post("/unlock", response_model=AccountUnlockResponse)
async def unlock_account_endpoint(
    payload: AccountUnlockRequest,
    session: AsyncSession = Depends(get_db_session),
    claims: TokenClaims = Depends(get_current_claims),
) -> AccountUnlockResponse:
    """Unlock a locked customer account. Fails if the account is not currently locked."""
    require_customer_access(payload.customer_id, claims)
    account = await unlock_account(
        session, payload.customer_id, payload.reason, actor=_UNLOCK_ACTOR
    )
    return AccountUnlockResponse(
        account_id=account.id,
        status=account.status,
        failed_login_attempts=account.failed_login_attempts,
        message="Account unlocked successfully.",
    )

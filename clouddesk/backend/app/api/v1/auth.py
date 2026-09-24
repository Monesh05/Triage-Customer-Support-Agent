# app/api/v1/auth.py
# Purpose: Phase 10 authentication endpoints (spec section 27): customer login and staff login,
#          each issuing a short-lived JWT (app.core.security) on success. Both are rate-limited
#          (app.core.rate_limit) as brute-force protection (org policy A07).
# Author: CloudDesk Team
# Date: 2026-09-24

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.core.security import AuthRole
from app.database.session import get_db_session
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth_service import InvalidCredentialsError, authenticate_customer, authenticate_staff

router = APIRouter(prefix="/auth", tags=["auth"])

_INVALID_CREDENTIALS_DETAIL: str = "Invalid email or password"


@router.post("/login", response_model=TokenResponse)
@limiter.limit(lambda: get_settings().rate_limit_login)
async def customer_login(
    request: Request,  # noqa: ARG001 - required by slowapi to key the rate limit by client IP.
    payload: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """Customer portal login. Returns a short-lived JWT carrying the customer's own id/role."""
    try:
        token = await authenticate_customer(session, payload.email, payload.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=_INVALID_CREDENTIALS_DETAIL) from exc
    return TokenResponse(
        access_token=token,
        expires_in_minutes=get_settings().jwt_access_token_expire_minutes,
        role=AuthRole.CUSTOMER.value,
    )


@router.post("/staff/login", response_model=TokenResponse)
@limiter.limit(lambda: get_settings().rate_limit_login)
async def staff_login(
    request: Request,  # noqa: ARG001 - required by slowapi to key the rate limit by client IP.
    payload: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """Support-console staff login. Returns a short-lived JWT carrying the staff role claim."""
    try:
        token = await authenticate_staff(session, payload.email, payload.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=_INVALID_CREDENTIALS_DETAIL) from exc
    return TokenResponse(
        access_token=token,
        expires_in_minutes=get_settings().jwt_access_token_expire_minutes,
        role=AuthRole.STAFF.value,
    )

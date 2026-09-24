# app/api/deps.py
# Purpose: FastAPI dependencies for Phase 10 authentication/authorization (spec section 27):
#          decode a bearer JWT into typed claims, and enforce the two authorization shapes every
#          protected route needs —
#            (1) a customer-facing route derives the acting customer id ENTIRELY from the token,
#                never from a client-supplied path/body param (org policy A01: "never trust
#                client-supplied roles" / IDOR prevention), and
#            (2) an internal staff-only route (`require_staff_role`) rejects any non-staff token.
#          A route that has BOTH a path `customer_id` AND must allow staff to act on any customer
#          (e.g. the Support Console viewing a specific customer's data) uses
#          `require_customer_access`, which allows staff unconditionally and a customer only when
#          the token's own id matches the requested one.
# Author: CloudDesk Team
# Date: 2026-09-24

import logging
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import AuthRole, TokenClaims, TokenError, decode_access_token

logger = logging.getLogger("clouddesk.api.auth")

_bearer_scheme = HTTPBearer(auto_error=False)

_UNAUTHENTICATED_DETAIL: str = "Not authenticated"
_FORBIDDEN_DETAIL: str = "You do not have access to this resource"


async def get_current_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> TokenClaims:
    """Decode and verify the bearer token on every protected request.

    Raises a 401 for a missing, malformed, or expired token — the specific reason is logged
    server-side only (org policy: never leak internals to users).
    """
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=_UNAUTHENTICATED_DETAIL)
    try:
        return decode_access_token(credentials.credentials)
    except TokenError as exc:
        logger.info("token_rejected reason=%s", exc)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=_UNAUTHENTICATED_DETAIL) from exc


async def get_current_customer_id(claims: TokenClaims = Depends(get_current_claims)) -> uuid.UUID:
    """The authenticated customer's own id, for a purely customer-scoped route (one with no path
    `customer_id` at all, e.g. POST /conversations). Rejects a staff token with a 403: staff act
    through the dedicated staff-only endpoints, not by pretending to be a customer.
    """
    if claims.role != AuthRole.CUSTOMER or claims.customer_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=_FORBIDDEN_DETAIL)
    return claims.customer_id


async def require_staff_role(claims: TokenClaims = Depends(get_current_claims)) -> TokenClaims:
    """Require an internal staff token (approvals/traces/cross-customer ticket list)."""
    if claims.role != AuthRole.STAFF:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=_FORBIDDEN_DETAIL)
    return claims


def require_customer_access(path_customer_id: uuid.UUID, claims: TokenClaims) -> None:
    """Authorize a route that takes `customer_id` as a path/body parameter: a staff token may act
    on any customer; a customer token may only act on itself. Raises 403 otherwise.

    Kept as a plain function (not a FastAPI dependency) since the customer id it checks comes from
    the route's own path/body parameter, not from another dependency — each router calls this
    explicitly after resolving both values.
    """
    if claims.role == AuthRole.STAFF:
        return
    if claims.role == AuthRole.CUSTOMER and claims.customer_id == path_customer_id:
        return
    raise HTTPException(status.HTTP_403_FORBIDDEN, detail=_FORBIDDEN_DETAIL)

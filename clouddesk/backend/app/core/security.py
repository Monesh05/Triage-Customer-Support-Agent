# app/core/security.py
# Purpose: Password hashing (bcrypt) and JWT issuance/verification for Phase 10 authentication
#          (spec section 27; org policy A02 "bcrypt or argon2", A07 "short-lived tokens, enforce
#          expiry"). Framework-agnostic — no FastAPI imports — so it can be unit tested and reused
#          by both the login endpoint and the auth dependencies without a circular import.
# Author: CloudDesk Team
# Date: 2026-09-24

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

import bcrypt
import jwt

from app.core.config import get_settings

# JWT registered/custom claim names, kept as constants rather than magic strings at every call
# site (org coding standard: no magic strings).
_CLAIM_SUBJECT: str = "sub"
_CLAIM_ROLE: str = "role"
_CLAIM_CUSTOMER_ID: str = "customer_id"
_CLAIM_EXPIRES_AT: str = "exp"
_CLAIM_ISSUED_AT: str = "iat"


class AuthRole(str, Enum):
    """The two authenticated identities this system distinguishes (spec section 27's
    customer-facing vs. internal-staff authorization split)."""

    CUSTOMER = "customer"
    STAFF = "staff"


class TokenError(Exception):
    """Raised when a bearer token is missing, malformed, expired, or otherwise not trustworthy.

    Deliberately a single error type: the caller (an auth dependency) always maps this to a 401,
    and the specific reason is logged, never leaked to the client (org policy: never leak
    internals to users).
    """


@dataclass(frozen=True)
class TokenClaims:
    """The decoded, verified contents of an access token."""

    role: AuthRole
    subject: str
    customer_id: uuid.UUID | None


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password with bcrypt. Never store/compare plaintext passwords anywhere."""
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Constant-time comparison of a plaintext password against its bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        # Malformed/unrecognized hash (e.g. a legacy or corrupted value) — treat as no match
        # rather than raising, so a bad stored hash never becomes a 500 that leaks internals.
        return False


def create_access_token(role: AuthRole, subject: str, customer_id: uuid.UUID | None = None) -> str:
    """Issue a short-lived signed JWT for a successful login.

    `subject` is the customer/staff id as a string (JWT `sub`); `customer_id` is additionally
    carried as its own claim (rather than only `sub`) so a customer-scoped auth dependency never
    needs to re-parse `sub` conditionally on `role`.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, str | int] = {
        _CLAIM_SUBJECT: subject,
        _CLAIM_ROLE: role.value,
        _CLAIM_ISSUED_AT: int(now.timestamp()),
        _CLAIM_EXPIRES_AT: int((now + timedelta(minutes=settings.jwt_access_token_expire_minutes)).timestamp()),
    }
    if customer_id is not None:
        payload[_CLAIM_CUSTOMER_ID] = str(customer_id)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> TokenClaims:
    """Verify a bearer token's signature and expiry, returning its typed claims.

    Raises:
        TokenError: on any invalid, expired, or malformed token.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("Token is invalid") from exc

    try:
        role = AuthRole(payload[_CLAIM_ROLE])
        subject = str(payload[_CLAIM_SUBJECT])
    except (KeyError, ValueError) as exc:
        raise TokenError("Token is missing required claims") from exc

    raw_customer_id = payload.get(_CLAIM_CUSTOMER_ID)
    customer_id: uuid.UUID | None = None
    if raw_customer_id is not None:
        try:
            customer_id = uuid.UUID(str(raw_customer_id))
        except ValueError as exc:
            raise TokenError("Token customer_id claim is malformed") from exc

    return TokenClaims(role=role, subject=subject, customer_id=customer_id)

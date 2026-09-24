# app/schemas/auth.py
# Purpose: Pydantic v2 request/response schemas for the Phase 10 authentication endpoints
#          (spec section 27). Never includes a password hash in any response.
# Author: CloudDesk Team
# Date: 2026-09-24

from pydantic import BaseModel, Field

PASSWORD_MIN_LENGTH: int = 8
EMAIL_MAX_LENGTH: int = 320


class LoginRequest(BaseModel):
    """Credentials for either POST /auth/login (customer) or POST /auth/staff/login (staff).

    `email` is validated as `str` (not pydantic's `EmailStr`) to avoid adding the
    `email-validator` dependency for this one field; format validity does not matter for
    authentication purposes anyway (an unknown/malformed email simply fails to match a stored
    row and is rejected as invalid credentials either way).
    """

    email: str = Field(min_length=1, max_length=EMAIL_MAX_LENGTH)
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=200)


class TokenResponse(BaseModel):
    """A successful login's issued access token (spec section 27: short-lived JWT)."""

    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    role: str

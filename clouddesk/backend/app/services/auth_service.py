# app/services/auth_service.py
# Purpose: Authenticate a customer or staff login by email/password, issue a JWT on success, and
#          audit every login attempt (spec section 27; org policy A09 "log auth/permission/
#          data-access events"). Deliberately does not distinguish "unknown email" from "wrong
#          password" in its raised error/message (org policy: never leak internals) — both are a
#          generic InvalidCredentialsError.
# Author: CloudDesk Team
# Date: 2026-09-24

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthRole, TokenClaims, create_access_token, verify_password
from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.enums import AuditActionType
from app.models.staff_user import StaffUser

logger = logging.getLogger("clouddesk.services.auth")

LOGIN_ACTOR_PREFIX: str = "auth:login"


class InvalidCredentialsError(Exception):
    """Raised when an email/password pair does not match any known customer or staff account."""


def _record_login_audit(
    session: AsyncSession, customer_id: object, action_type: AuditActionType, email: str, role: str
) -> None:
    """Stage a login audit-log row. `email` is safe to log (it identifies the login attempt for
    security review) but the password itself must never appear here or anywhere else in a log."""
    session.add(
        AuditLog(
            customer_id=customer_id,
            action_type=action_type,
            actor=f"{LOGIN_ACTOR_PREFIX}:{role}",
            details={"email": email, "role": role},
        )
    )


async def authenticate_customer(session: AsyncSession, email: str, password: str) -> str:
    """Verify customer credentials and return a signed access token.

    Raises:
        InvalidCredentialsError: unknown email, no password set, or a wrong password.
    """
    result = await session.execute(select(Customer).where(Customer.email == email))
    customer = result.scalar_one_or_none()

    if customer is None or not customer.password_hash or not verify_password(password, customer.password_hash):
        logger.warning("login_failed role=customer email=%s", email)
        _record_login_audit(session, None, AuditActionType.LOGIN_FAILED, email, AuthRole.CUSTOMER.value)
        await session.commit()
        raise InvalidCredentialsError("Invalid email or password")

    logger.info("login_succeeded role=customer customer_id=%s", customer.id)
    _record_login_audit(session, customer.id, AuditActionType.LOGIN_SUCCEEDED, email, AuthRole.CUSTOMER.value)
    await session.commit()
    return create_access_token(AuthRole.CUSTOMER, subject=str(customer.id), customer_id=customer.id)


async def authenticate_staff(session: AsyncSession, email: str, password: str) -> str:
    """Verify staff credentials and return a signed access token.

    Raises:
        InvalidCredentialsError: unknown email or a wrong password.
    """
    result = await session.execute(select(StaffUser).where(StaffUser.email == email))
    staff_user = result.scalar_one_or_none()

    if staff_user is None or not verify_password(password, staff_user.password_hash):
        logger.warning("login_failed role=staff email=%s", email)
        _record_login_audit(session, None, AuditActionType.LOGIN_FAILED, email, AuthRole.STAFF.value)
        await session.commit()
        raise InvalidCredentialsError("Invalid email or password")

    logger.info("login_succeeded role=staff staff_id=%s", staff_user.id)
    _record_login_audit(session, None, AuditActionType.LOGIN_SUCCEEDED, email, AuthRole.STAFF.value)
    await session.commit()
    return create_access_token(AuthRole.STAFF, subject=str(staff_user.id))


def is_customer(claims: TokenClaims) -> bool:
    """True if the decoded token identifies an authenticated customer."""
    return claims.role == AuthRole.CUSTOMER

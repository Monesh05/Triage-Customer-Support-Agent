# app/services/account_service.py
# Purpose: Business logic for account retrieval and the account-unlock operation. This will
#          later be wrapped as an agent tool, so unlock logic must be real and safe: it only
#          unlocks accounts that are actually locked, resets the failed-attempt counter, and
#          writes an audit log entry (spec sections 7, 22, 27).
# Author: CloudDesk Team
# Date: 2026-09-21

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.account import Account
from app.models.enums import AccountStatus, AuditActionType
from app.services.audit_service import record_audit
from app.services.exceptions import InvalidStateError, NotFoundError

logger = logging.getLogger(__name__)

RESET_FAILED_ATTEMPTS: int = 0


async def get_account_by_customer_id(
    session: AsyncSession, customer_id: uuid.UUID
) -> Account:
    """Fetch an account by its owning customer id or raise NotFoundError."""
    result = await session.execute(
        select(Account).where(Account.customer_id == customer_id)
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise NotFoundError(f"Account for customer {customer_id} not found")
    return account


async def unlock_account(
    session: AsyncSession, customer_id: uuid.UUID, reason: str, actor: str
) -> Account:
    """Unlock a locked customer account, reset failed attempts, and audit the action.

    Raises:
        NotFoundError: if no account exists for the customer.
        InvalidStateError: if the account is not currently locked.
    """
    account = await get_account_by_customer_id(session, customer_id)

    if account.status != AccountStatus.LOCKED:
        raise InvalidStateError(
            f"Account {account.id} is not locked (status={account.status.value})"
        )

    account.status = AccountStatus.ACTIVE
    account.failed_login_attempts = RESET_FAILED_ATTEMPTS

    record_audit(
        session, customer_id, AuditActionType.ACCOUNT_UNLOCK, actor,
        {"reason": reason, "account_id": str(account.id)},
    )

    try:
        await session.commit()
    except Exception:
        logger.exception("Failed to commit account unlock for customer %s", customer_id)
        await session.rollback()
        raise

    await session.refresh(account)
    logger.info("Account %s unlocked for customer %s", account.id, customer_id)
    return account


def is_account_lockable(failed_login_attempts: int) -> bool:
    """Return True if the given failed-attempt count meets the lockout threshold."""
    settings = get_settings()
    return failed_login_attempts >= settings.account_lockout_threshold

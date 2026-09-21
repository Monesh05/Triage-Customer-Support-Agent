# tests/test_account_service.py
# Purpose: Unit tests for app.services.account_service (unlock happy path, invalid state,
#          not-found, and the lockout-threshold helper).
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AccountStatus
from app.services.account_service import (
    is_account_lockable,
    unlock_account,
)
from app.services.exceptions import InvalidStateError, NotFoundError
from tests.conftest import new_id
from tests.factories import create_customer_with_account, create_org_and_plan


async def test_unlock_account_happy_path(db_session: AsyncSession) -> None:
    org, _free, pro = await create_org_and_plan(db_session)
    customer = await create_customer_with_account(
        db_session, org, pro, account_status=AccountStatus.LOCKED, failed_login_attempts=7
    )

    account = await unlock_account(db_session, customer.id, reason="verified", actor="test")

    assert account.status == AccountStatus.ACTIVE
    assert account.failed_login_attempts == 0


async def test_unlock_account_not_locked_raises_invalid_state(db_session: AsyncSession) -> None:
    org, _free, pro = await create_org_and_plan(db_session)
    customer = await create_customer_with_account(db_session, org, pro, account_status=AccountStatus.ACTIVE)

    with pytest.raises(InvalidStateError):
        await unlock_account(db_session, customer.id, reason="n/a", actor="test")


async def test_unlock_account_unknown_customer_raises_not_found(db_session: AsyncSession) -> None:
    with pytest.raises(NotFoundError):
        await unlock_account(db_session, new_id(), reason="n/a", actor="test")


@pytest.mark.parametrize(
    ("attempts", "expected"),
    [(0, False), (4, False), (5, True), (9, True)],
)
def test_is_account_lockable_threshold(attempts: int, expected: bool) -> None:
    assert is_account_lockable(attempts) is expected

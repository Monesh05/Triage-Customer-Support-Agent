# tests/test_subscription_service.py
# Purpose: Unit tests for app.services.subscription_service — stale-entitlement detection
#          and the entitlement-refresh operation (happy path for a stale entitlement, a
#          no-op refresh for an already-synced entitlement, and not-found for an unknown
#          customer).
# Author: CloudDesk Team
# Date: 2026-09-21

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.exceptions import NotFoundError
from app.services.subscription_service import is_entitlement_stale, refresh_entitlement
from tests.conftest import new_id
from tests.factories import create_customer_with_account, create_org_and_plan


async def test_refresh_entitlement_fixes_stale_plan_mismatch(db_session: AsyncSession) -> None:
    org, free, pro = await create_org_and_plan(db_session)
    customer = await create_customer_with_account(db_session, org, pro)
    subscription = customer.subscriptions[0]
    # Simulate a stale sync: entitlement still points at the Free plan.
    subscription.entitlement.granted_plan_id = free.id
    subscription.entitlement.granted_api_rate_limit = free.api_rate_limit
    await db_session.flush()

    assert is_entitlement_stale(subscription) is True

    updated_subscription, was_stale = await refresh_entitlement(
        db_session, customer.id, reason="test", actor="test"
    )

    assert was_stale is True
    assert updated_subscription.entitlement.granted_plan_id == pro.id
    assert updated_subscription.entitlement.granted_api_rate_limit == pro.api_rate_limit


async def test_refresh_entitlement_is_noop_when_already_synced(db_session: AsyncSession) -> None:
    org, _free, pro = await create_org_and_plan(db_session)
    customer = await create_customer_with_account(db_session, org, pro)

    _subscription, was_stale = await refresh_entitlement(
        db_session, customer.id, reason="test", actor="test"
    )

    assert was_stale is False


async def test_refresh_entitlement_unknown_customer_raises_not_found(db_session: AsyncSession) -> None:
    with pytest.raises(NotFoundError):
        await refresh_entitlement(db_session, new_id(), reason="test", actor="test")

# tests/test_tools_account.py
# Purpose: Tests for app.tools.account — customer/account lookup, login-history/permissions/
#          MFA snapshots, subscription entitlements, and entitlement refresh. Uses
#          `committed_session` since these tools open their own DB connection.
# Author: CloudDesk Team
# Date: 2026-09-21

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AccountStatus
from app.tools import account
from tests.conftest import new_id
from tests.factories import create_customer_with_account, create_org_and_plan


async def _register(committed_session: AsyncSession, org) -> None:
    committed_session.info["created_org_ids"].append(org.id)


async def test_get_customer_happy_path(committed_session: AsyncSession) -> None:
    org, _free, pro = await create_org_and_plan(committed_session)
    customer = await create_customer_with_account(committed_session, org, pro)
    await committed_session.commit()
    await _register(committed_session, org)

    result = await account.get_customer(customer.id)

    assert result.success is True
    assert result.data.id == customer.id


async def test_get_customer_not_found(committed_session: AsyncSession) -> None:
    result = await account.get_customer(new_id())

    assert result.success is False
    assert result.data is None


async def test_get_customer_invalid_uuid_input() -> None:
    result = await account.get_customer("not-a-uuid")

    assert result.success is False
    assert "Invalid customer_id" in result.error


async def test_get_account_happy_path(committed_session: AsyncSession) -> None:
    org, _free, pro = await create_org_and_plan(committed_session)
    customer = await create_customer_with_account(
        committed_session, org, pro, account_status=AccountStatus.LOCKED, failed_login_attempts=6
    )
    await committed_session.commit()
    await _register(committed_session, org)

    result = await account.get_account(customer.id)

    assert result.success is True
    assert result.data.status == AccountStatus.LOCKED
    assert result.data.failed_login_attempts == 6


async def test_get_login_history_reflects_only_real_fields(committed_session: AsyncSession) -> None:
    org, _free, pro = await create_org_and_plan(committed_session)
    customer = await create_customer_with_account(
        committed_session, org, pro, failed_login_attempts=3
    )
    await committed_session.commit()
    await _register(committed_session, org)

    result = await account.get_login_history(customer.id)

    assert result.success is True
    assert result.data.failed_login_attempts == 3
    assert result.data.last_login_at is None  # never fabricated


async def test_get_account_permissions_happy_path(committed_session: AsyncSession) -> None:
    org, _free, pro = await create_org_and_plan(committed_session)
    customer = await create_customer_with_account(committed_session, org, pro)
    await committed_session.commit()
    await _register(committed_session, org)

    result = await account.get_account_permissions(customer.id)

    assert result.success is True
    assert result.data.permissions == ["read"]


async def test_check_mfa_status_defaults_false(committed_session: AsyncSession) -> None:
    org, _free, pro = await create_org_and_plan(committed_session)
    customer = await create_customer_with_account(committed_session, org, pro)
    await committed_session.commit()
    await _register(committed_session, org)

    result = await account.check_mfa_status(customer.id)

    assert result.success is True
    assert result.data.mfa_enabled is False


async def test_get_subscription_entitlements_happy_path(committed_session: AsyncSession) -> None:
    org, _free, pro = await create_org_and_plan(committed_session)
    customer = await create_customer_with_account(committed_session, org, pro)
    await committed_session.commit()
    await _register(committed_session, org)

    result = await account.get_subscription_entitlements(customer.id)

    assert result.success is True
    assert result.data[0].granted_plan_id == pro.id


async def test_refresh_entitlement_fixes_stale_mismatch(committed_session: AsyncSession) -> None:
    org, free, pro = await create_org_and_plan(committed_session)
    customer = await create_customer_with_account(committed_session, org, pro)
    subscription = customer.subscriptions[0]
    subscription.entitlement.granted_plan_id = free.id
    subscription.entitlement.granted_api_rate_limit = free.api_rate_limit
    await committed_session.commit()
    await _register(committed_session, org)

    result = await account.refresh_entitlement(customer.id, reason="test")

    assert result.success is True
    assert result.data.was_stale is True
    assert result.data.granted_plan_id == pro.id


async def test_refresh_entitlement_not_found(committed_session: AsyncSession) -> None:
    result = await account.refresh_entitlement(new_id(), reason="test")

    assert result.success is False

# app/tools/account.py
# Purpose: Account Agent tool layer (spec section 11), plus the shared `get_customer` lookup
#          (used across agents for basic identity context). Covers account access, login
#          state, permissions, MFA, and subscription entitlements/refresh. Each function opens
#          its own session via app.database.session.get_session() and delegates to
#          app.services.* — no raw SQL, no direct DB access.
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid

from app.database.session import get_session
from app.schemas.account import AccountResponse
from app.schemas.customer import CustomerResponse
from app.schemas.subscription import EntitlementResponse
from app.services import account_service, customer_service, subscription_service
from app.services.exceptions import NotFoundError
from app.tools.base import ToolInputError, ToolResult, log_tool_call, parse_uuid
from app.tools.schemas import (
    AccountPermissionsData,
    EntitlementRefreshData,
    LoginHistoryData,
    MfaStatusData,
)

DEFAULT_REFRESH_ACTOR: str = "account_agent"


async def get_customer(customer_id: str | uuid.UUID) -> ToolResult[CustomerResponse]:
    """Fetch basic customer identity/status info."""
    try:
        cid = parse_uuid(customer_id, "customer_id")
        async with get_session() as session:
            customer = await customer_service.get_customer_by_id(session, cid)
            data = CustomerResponse.model_validate(customer)
        return ToolResult(success=True, data=data)
    except (ToolInputError, NotFoundError) as exc:
        return ToolResult(success=False, error=str(exc))
    except Exception as exc:  # noqa: BLE001
        return ToolResult(success=False, error=f"Unexpected error in get_customer: {exc}")


async def get_account(customer_id: str | uuid.UUID) -> ToolResult[AccountResponse]:
    """Fetch the login/security-state account record for a customer."""
    try:
        cid = parse_uuid(customer_id, "customer_id")
        async with get_session() as session:
            account = await account_service.get_account_by_customer_id(session, cid)
            data = AccountResponse.model_validate(account)
        return ToolResult(success=True, data=data)
    except (ToolInputError, NotFoundError) as exc:
        return ToolResult(success=False, error=str(exc))
    except Exception as exc:  # noqa: BLE001
        return ToolResult(success=False, error=f"Unexpected error in get_account: {exc}")


async def get_login_history(customer_id: str | uuid.UUID) -> ToolResult[LoginHistoryData]:
    """Return the account's login-security snapshot.

    LIMITATION: Phase 1 has no login-history table — only the most recent login timestamp/IP
    and the failed-attempt counter exist. This returns exactly that; it never fabricates a
    history of past logins.
    """
    try:
        cid = parse_uuid(customer_id, "customer_id")
        async with get_session() as session:
            account = await account_service.get_account_by_customer_id(session, cid)
            data = LoginHistoryData(
                account_id=account.id,
                customer_id=account.customer_id,
                last_login_at=account.last_login_at,
                last_login_ip=account.last_login_ip,
                failed_login_attempts=account.failed_login_attempts,
                account_status=account.status,
            )
        return ToolResult(success=True, data=data)
    except (ToolInputError, NotFoundError) as exc:
        return ToolResult(success=False, error=str(exc))
    except Exception as exc:  # noqa: BLE001
        return ToolResult(success=False, error=f"Unexpected error in get_login_history: {exc}")


async def get_account_permissions(
    customer_id: str | uuid.UUID,
) -> ToolResult[AccountPermissionsData]:
    """Return the account's stored permission grants, verbatim (no derived/invented logic)."""
    try:
        cid = parse_uuid(customer_id, "customer_id")
        async with get_session() as session:
            account = await account_service.get_account_by_customer_id(session, cid)
            data = AccountPermissionsData(
                account_id=account.id,
                customer_id=account.customer_id,
                permissions=list(account.permissions),
            )
        return ToolResult(success=True, data=data)
    except (ToolInputError, NotFoundError) as exc:
        return ToolResult(success=False, error=str(exc))
    except Exception as exc:  # noqa: BLE001
        return ToolResult(success=False, error=f"Unexpected error in get_account_permissions: {exc}")


async def check_mfa_status(customer_id: str | uuid.UUID) -> ToolResult[MfaStatusData]:
    """Return whether MFA is enabled for the account (spec section 11)."""
    try:
        cid = parse_uuid(customer_id, "customer_id")
        async with get_session() as session:
            account = await account_service.get_account_by_customer_id(session, cid)
            data = MfaStatusData(
                account_id=account.id, customer_id=account.customer_id, mfa_enabled=account.mfa_enabled
            )
        return ToolResult(success=True, data=data)
    except (ToolInputError, NotFoundError) as exc:
        return ToolResult(success=False, error=str(exc))
    except Exception as exc:  # noqa: BLE001
        return ToolResult(success=False, error=f"Unexpected error in check_mfa_status: {exc}")


async def get_subscription_entitlements(
    customer_id: str | uuid.UUID,
) -> ToolResult[list[EntitlementResponse]]:
    """Return the entitlement snapshot for each of a customer's subscriptions."""
    try:
        cid = parse_uuid(customer_id, "customer_id")
        async with get_session() as session:
            subs = await subscription_service.get_subscriptions_by_customer(session, cid)
            data = [
                EntitlementResponse.model_validate(s.entitlement)
                for s in subs
                if s.entitlement is not None
            ]
        return ToolResult(success=True, data=data)
    except (ToolInputError, NotFoundError) as exc:
        return ToolResult(success=False, error=str(exc))
    except Exception as exc:  # noqa: BLE001
        return ToolResult(
            success=False, error=f"Unexpected error in get_subscription_entitlements: {exc}"
        )


async def refresh_entitlement(
    customer_id: str | uuid.UUID, reason: str = "manual_refresh", actor: str = DEFAULT_REFRESH_ACTOR
) -> ToolResult[EntitlementRefreshData]:
    """Re-sync a customer's entitlement to match their current subscription plan.

    Sensitive/mutating action (spec section 22 lists subscription/entitlement changes as
    requiring approval upstream of this tool); logged for audit per A09.
    """
    try:
        cid = parse_uuid(customer_id, "customer_id")
        async with get_session() as session:
            subscription, was_stale = await subscription_service.refresh_entitlement(
                session, cid, reason, actor
            )
            log_tool_call("refresh_entitlement", cid, f"was_stale={was_stale}")
            entitlement = subscription.entitlement
            data = EntitlementRefreshData(
                subscription_id=subscription.id,
                was_stale=was_stale,
                granted_plan_id=entitlement.granted_plan_id,
                granted_api_rate_limit=entitlement.granted_api_rate_limit,
                granted_features=list(entitlement.granted_features),
            )
        return ToolResult(success=True, data=data)
    except (ToolInputError, NotFoundError) as exc:
        return ToolResult(success=False, error=str(exc))
    except Exception as exc:  # noqa: BLE001
        return ToolResult(success=False, error=f"Unexpected error in refresh_entitlement: {exc}")

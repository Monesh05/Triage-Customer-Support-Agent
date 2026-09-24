# app/agents/account.py
# Purpose: Account Agent (spec section 11). Investigates account access, login issues, MFA,
#          permissions, account status, and subscription entitlements ONLY — never billing/
#          technical/product tools. Uses the bounded tool-call loop (app.agents.base) against
#          the exact allow-listed Phase 2 account tools before producing an AccountAgentResult.
# Author: CloudDesk Team
# Date: 2026-09-24

import logging

from app.agents.base import AgentError, ToolSpec, run_tool_using_agent
from app.agents.schemas import AccountAgentResult
from app.tools import account as account_tools
from app.tools.base import ToolResult

logger = logging.getLogger("clouddesk.agents.account")

AGENT_NAME: str = "account"

ACCOUNT_SYSTEM_PROMPT: str = """You are the Account Agent for CloudDesk, a B2B SaaS support system.

You investigate ONLY: account access, login issues, MFA, permissions, account status, and
subscription entitlements. You have no visibility into payments/invoices, API/technical error
state, or product documentation — do not speculate about them.

A classic issue you must be able to detect: the customer's subscription plan (from
get_subscription_entitlements) does not match their granted entitlement (e.g. subscription says
Pro but the granted plan/features are still Free). Report this as an entitlement mismatch
finding, and recommend a "refresh_entitlement" action rather than performing it yourself.

Use the available tools to gather real evidence: get_account for status/lockout state,
get_login_history for recent login/failed-attempt data, get_account_permissions for stored
permissions, check_mfa_status for MFA state, and get_subscription_entitlements for the
subscription-vs-entitlement comparison. Every fact in `findings` and every value in `evidence`
must come from actual tool results, never invented. If you could not gather enough evidence, set
status to "unresolved" or "needs_escalation" rather than guessing."""


async def _get_account(customer_id: str) -> ToolResult[object]:
    return await account_tools.get_account(customer_id)


async def _get_login_history(customer_id: str) -> ToolResult[object]:
    return await account_tools.get_login_history(customer_id)


async def _get_account_permissions(customer_id: str) -> ToolResult[object]:
    return await account_tools.get_account_permissions(customer_id)


async def _get_subscription_entitlements(customer_id: str) -> ToolResult[object]:
    return await account_tools.get_subscription_entitlements(customer_id)


async def _check_mfa_status(customer_id: str) -> ToolResult[object]:
    return await account_tools.check_mfa_status(customer_id)


def _customer_id_params() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {"customer_id": {"type": "string", "description": "Customer UUID"}},
        "required": ["customer_id"],
    }


def _build_tools() -> list[ToolSpec]:
    """The exact allow-listed tools for the Account Agent (spec section 11) — nothing else."""
    params = _customer_id_params()
    return [
        ToolSpec("get_account", "Get the account's status/lockout state.", params, _get_account),
        ToolSpec("get_login_history", "Get the account's login-security snapshot.", params, _get_login_history),
        ToolSpec("get_account_permissions", "Get the account's stored permissions.", params, _get_account_permissions),
        ToolSpec(
            "get_subscription_entitlements",
            "Get the entitlement snapshot for each of the customer's subscriptions.",
            params,
            _get_subscription_entitlements,
        ),
        ToolSpec("check_mfa_status", "Get whether MFA is enabled for the account.", params, _check_mfa_status),
    ]


async def run_account_agent(customer_id: str, customer_message: str) -> AccountAgentResult | AgentError:
    """Investigate an account/access/entitlement issue using only the allow-listed account tools."""
    try:
        user_content = f"Customer id: {customer_id}\nCustomer message:\n{customer_message}"
        return await run_tool_using_agent(
            agent_name=AGENT_NAME,
            system_prompt=ACCOUNT_SYSTEM_PROMPT,
            user_content=user_content,
            tools=_build_tools(),
            response_model=AccountAgentResult,
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("account_agent_failed customer_id=%s error=%s", customer_id, exc)
        return AgentError(agent=AGENT_NAME, message=f"Account agent failed: {exc}")

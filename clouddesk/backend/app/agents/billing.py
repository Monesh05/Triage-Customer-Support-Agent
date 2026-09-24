# app/agents/billing.py
# Purpose: Billing Agent (spec section 10). Investigates subscriptions, payments, invoices,
#          duplicate charges, refunds, and billing policy ONLY — never account/technical/
#          product tools. Uses a bounded tool-call loop (app.agents.base) against the exact
#          allow-listed Phase 2 billing tools before producing a structured BillingAgentResult.
# Author: CloudDesk Team
# Date: 2026-09-24

import logging

from app.agents.base import AgentError, ToolSpec, run_tool_using_agent
from app.agents.schemas import BillingAgentResult
from app.tools import billing as billing_tools
from app.tools.base import ToolResult

logger = logging.getLogger("clouddesk.agents.billing")

AGENT_NAME: str = "billing"

BILLING_SYSTEM_PROMPT: str = """You are the Billing Agent for CloudDesk, a B2B SaaS support system.

You investigate ONLY: subscriptions, payments, invoices, duplicate charges, refunds, billing
policy, and cancellations. You have no visibility into account/login state, API/technical
issues, or product documentation — do not speculate about them.

Use the available tools to gather real evidence before concluding anything. Look at actual
payment and invoice records; do not assume a duplicate charge exists without confirming it via
get_payment_history. If a refund seems warranted, call calculate_refund to check eligibility and
amount, and consult get_billing_policy for the applicable rule before recommending one.

You may call create_refund_request to create a refund request, but this ONLY ever creates a
PENDING_APPROVAL request — it never completes a refund. NEVER claim in your findings or
recommended_actions that a refund was "processed" or "issued". If you create a refund request,
report it as "a refund request was created and is pending approval".

Every fact in `findings` and every id in `evidence` must come from actual tool results, never
invented. If you could not gather enough evidence, set status to "unresolved" or
"needs_escalation" rather than guessing."""


async def _get_subscription(customer_id: str) -> ToolResult[object]:
    return await billing_tools.get_subscription(customer_id)


async def _get_payment_history(customer_id: str) -> ToolResult[object]:
    return await billing_tools.get_payment_history(customer_id)


async def _get_invoice(customer_id: str) -> ToolResult[object]:
    return await billing_tools.get_invoice(customer_id)


async def _calculate_refund(payment_id: str) -> ToolResult[object]:
    return await billing_tools.calculate_refund(payment_id)


async def _get_billing_policy(policy_key: str) -> ToolResult[object]:
    return await billing_tools.get_billing_policy(policy_key)


async def _create_refund_request(payment_id: str, reason: str) -> ToolResult[object]:
    return await billing_tools.create_refund_request(payment_id, reason)


def _build_tools() -> list[ToolSpec]:
    """The exact allow-listed tools for the Billing Agent (spec section 10) — nothing else."""
    customer_id_params = {
        "type": "object",
        "properties": {"customer_id": {"type": "string", "description": "Customer UUID"}},
        "required": ["customer_id"],
    }
    return [
        ToolSpec("get_subscription", "Get a customer's subscriptions and plans.", customer_id_params, _get_subscription),
        ToolSpec("get_payment_history", "Get a customer's payment history.", customer_id_params, _get_payment_history),
        ToolSpec("get_invoice", "Get a customer's invoices.", customer_id_params, _get_invoice),
        ToolSpec(
            "calculate_refund",
            "Compute the refundable amount for a payment without creating a refund.",
            {
                "type": "object",
                "properties": {"payment_id": {"type": "string", "description": "Payment UUID"}},
                "required": ["payment_id"],
            },
            _calculate_refund,
        ),
        ToolSpec(
            "get_billing_policy",
            "Look up a billing/refund/cancellation policy by its key (e.g. 'refund_rules').",
            {
                "type": "object",
                "properties": {"policy_key": {"type": "string"}},
                "required": ["policy_key"],
            },
            _get_billing_policy,
        ),
        ToolSpec(
            "create_refund_request",
            "Create a PENDING_APPROVAL refund request for a payment. Does not complete a refund.",
            {
                "type": "object",
                "properties": {
                    "payment_id": {"type": "string", "description": "Payment UUID"},
                    "reason": {"type": "string"},
                },
                "required": ["payment_id", "reason"],
            },
            _create_refund_request,
        ),
    ]


async def run_billing_agent(customer_id: str, customer_message: str) -> BillingAgentResult | AgentError:
    """Investigate a billing issue for `customer_id` using only the allow-listed billing tools."""
    try:
        user_content = f"Customer id: {customer_id}\nCustomer message:\n{customer_message}"
        return await run_tool_using_agent(
            agent_name=AGENT_NAME,
            system_prompt=BILLING_SYSTEM_PROMPT,
            user_content=user_content,
            tools=_build_tools(),
            response_model=BillingAgentResult,
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("billing_agent_failed customer_id=%s error=%s", customer_id, exc)
        return AgentError(agent=AGENT_NAME, message=f"Billing agent failed: {exc}")

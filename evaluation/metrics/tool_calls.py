# evaluation/metrics/tool_calls.py
# Purpose: Tool-call accuracy (spec section 28). HEURISTIC, not exact ground truth: there is no
#          labeled "correct tool sequence" per ticket, so this scores whether the tools a
#          category's relevant specialist(s) actually called (from the Phase 7 `AgentRun.
#          tool_calls` trace, app/observability/tracer.py's `record_tool_call`) overlap with a
#          reasonable expected-tools-per-category mapping (spec sections 10-12's "allowed
#          tools" lists). A ticket with no expected tools defined (e.g. "ambiguous"/"escalation",
#          which may never reach a specialist at all) is excluded from the average rather than
#          scored as a failure.
# Author: CloudDesk Team
# Date: 2026-09-24

from evaluation.datasets.schema import (
    CATEGORY_ACCOUNT,
    CATEGORY_BILLING,
    CATEGORY_FALSE_POSITIVE,
    CATEGORY_MULTI_INTENT,
    CATEGORY_POLICY_SENSITIVE,
    CATEGORY_PRODUCT,
    CATEGORY_TECHNICAL,
)
from evaluation.metrics.models import TicketOutcome

# Spec sections 10 (Billing), 11 (Account), 12 (Technical), 13/14 (Product) "allowed tools" lists.
EXPECTED_TOOLS_BY_CATEGORY: dict[str, set[str]] = {
    CATEGORY_BILLING: {"get_subscription", "get_payment_history", "get_invoice", "calculate_refund",
                        "get_billing_policy", "create_refund_request"},
    CATEGORY_POLICY_SENSITIVE: {"get_billing_policy", "get_payment_history", "calculate_refund"},
    CATEGORY_ACCOUNT: {"get_account", "get_login_history", "get_account_permissions",
                        "get_subscription_entitlements", "check_mfa_status"},
    CATEGORY_TECHNICAL: {"get_api_usage", "get_api_key_status", "get_service_status",
                          "search_error_logs", "get_recent_incidents", "search_product_docs"},
    CATEGORY_FALSE_POSITIVE: {"get_api_usage", "get_service_status", "search_error_logs"},
    CATEGORY_PRODUCT: {"search_product_docs"},
    CATEGORY_MULTI_INTENT: {"get_payment_history", "get_subscription", "get_account",
                             "get_api_usage", "get_subscription_entitlements"},
}


def _called_tool_names(outcome: TicketOutcome) -> set[str]:
    names: set[str] = set()
    for run in outcome.trace:
        names.update(entry.get("tool", "") for entry in run.tool_calls)
    names.discard("")
    return names


def tool_call_accuracy(outcomes: list[TicketOutcome]) -> float:
    """Mean Jaccard overlap between a category's expected tool set and the tools actually
    called across a ticket's whole trace. Documented heuristic (see module docstring)."""
    scores: list[float] = []
    for outcome in outcomes:
        if not outcome.succeeded:
            continue
        expected = EXPECTED_TOOLS_BY_CATEGORY.get(outcome.record.category)
        if not expected:
            continue
        called = _called_tool_names(outcome)
        if not called:
            scores.append(0.0)
            continue
        scores.append(len(expected & called) / len(expected | called))
    return sum(scores) / len(scores) if scores else 0.0

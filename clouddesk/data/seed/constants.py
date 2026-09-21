# constants.py
# Purpose: Static reference data (plans, organizations, support policies) used by the
#          CloudDesk seed script. Kept separate from seed.py so plan/policy definitions can
#          be reused (e.g. by future tool/agent code) without pulling in seeding logic.
# Author: CloudDesk Team
# Date: 2026-09-21

from typing import TypedDict


class PlanSeed(TypedDict):
    name: str
    price_monthly: float
    api_rate_limit: int
    features: list[str]


PLAN_SEEDS: list[PlanSeed] = [
    {
        "name": "Free",
        "price_monthly": 0.00,
        "api_rate_limit": 1_000,
        "features": ["community_support"],
    },
    {
        "name": "Pro",
        "price_monthly": 49.00,
        "api_rate_limit": 50_000,
        "features": ["community_support", "priority_email_support", "api_access"],
    },
    {
        "name": "Business",
        "price_monthly": 199.00,
        "api_rate_limit": 250_000,
        "features": [
            "community_support",
            "priority_email_support",
            "api_access",
            "sso",
            "audit_logs",
        ],
    },
    {
        "name": "Enterprise",
        "price_monthly": 999.00,
        "api_rate_limit": 2_000_000,
        "features": [
            "community_support",
            "priority_email_support",
            "api_access",
            "sso",
            "audit_logs",
            "dedicated_support",
            "custom_contracts",
        ],
    },
]

ORGANIZATION_SEEDS: list[dict[str, str]] = [
    {"name": "Acme Corporation", "domain": "acme.example"},
    {"name": "Globex Industries", "domain": "globex.example"},
    {"name": "Initech Software", "domain": "initech.example"},
    {"name": "Umbrella Analytics", "domain": "umbrella.example"},
    {"name": "Stark Cloud Systems", "domain": "starkcloud.example"},
]

SUPPORT_POLICY_SEEDS: list[dict] = [
    {
        "policy_key": "refund_rules",
        "title": "Refund Rules",
        "description": "Rules governing when a customer payment may be refunded.",
        "rules": {
            "duplicate_charge_full_refund": True,
            "requires_human_approval": True,
            "max_auto_refund_amount_usd": 0,
            "refund_window_days": 90,
        },
    },
    {
        "policy_key": "cancellation_rules",
        "title": "Cancellation Rules",
        "description": "Rules governing subscription cancellations.",
        "rules": {
            "prorate_on_cancel": False,
            "effective_at_period_end": True,
        },
    },
    {
        "policy_key": "plan_upgrade_behavior",
        "title": "Plan Upgrade Behavior",
        "description": "Rules describing how entitlements should sync after a plan change.",
        "rules": {
            "entitlement_sync_expected_within_minutes": 5,
            "manual_refresh_endpoint": "/api/v1/entitlements/refresh",
        },
    },
    {
        "policy_key": "account_recovery_rules",
        "title": "Account Recovery Rules",
        "description": "Rules governing unlocking a locked account.",
        "rules": {
            "lockout_threshold_failed_attempts": 5,
            "requires_identity_verification": True,
        },
    },
    {
        "policy_key": "escalation_rules",
        "title": "Escalation Rules",
        "description": "Rules describing when a support issue must be escalated to a human.",
        "rules": {
            "escalate_on_repeated_qa_failure": True,
            "escalate_on_explicit_human_request": True,
            "escalate_on_low_confidence": True,
        },
    },
]

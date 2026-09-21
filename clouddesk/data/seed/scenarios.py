# scenarios.py
# Purpose: Composes builders.py factory functions into full customer scenarios (account +
#          subscription + entitlement + payments + invoices + API key + usage), covering the
#          realistic-and-unhappy-path seed data mandated by spec section 6: normal customers,
#          duplicate payments, failed/pending payments, stale entitlements, locked accounts,
#          and false-positive high-usage customers.
# Author: CloudDesk Team
# Date: 2026-09-21

from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.enums import (
    AccountStatus,
    ApiKeyStatus,
    CustomerStatus,
    InvoiceStatus,
    PaymentMethod,
    PaymentStatus,
    SubscriptionStatus,
)
from app.models.organization import Organization
from app.models.plan import Plan
from data.seed.builders import (
    build_account,
    build_api_key,
    build_customer,
    build_entitlement,
    build_invoice,
    build_payment,
    build_subscription,
    build_usage_record,
    utc,
)

CURRENT_PERIOD_START = utc(2026, 9, 1)
CURRENT_PERIOD_END = utc(2026, 9, 30, 23)


def _base_customer_stack(
    session: AsyncSession,
    organization: Organization,
    name: str,
    email: str,
    plan: Plan,
    subscription_status: SubscriptionStatus = SubscriptionStatus.ACTIVE,
) -> tuple[Customer, object]:
    """Create + register a customer, account, and subscription. Returns (customer, subscription)."""
    customer = build_customer(organization, name, email, CustomerStatus.ACTIVE)
    account = build_account(customer)
    subscription = build_subscription(
        customer,
        plan,
        subscription_status,
        start_date=date(2026, 1, 15),
        renewal_date=date(2026, 10, 15),
    )
    session.add_all([customer, account, subscription])
    return customer, subscription


def seed_normal_customer(
    session: AsyncSession, organization: Organization, name: str, email: str, plan: Plan
) -> Customer:
    """A healthy customer: synced entitlement, one successful payment, paid invoice."""
    customer, subscription = _base_customer_stack(session, organization, name, email, plan)
    session.add(build_entitlement(subscription, plan, last_synced_at=utc(2026, 9, 1)))
    session.add(
        build_payment(
            customer, subscription, plan.price_monthly, PaymentStatus.SUCCEEDED,
            PaymentMethod.CARD, CURRENT_PERIOD_START, CURRENT_PERIOD_START, CURRENT_PERIOD_END,
        )
    )
    session.add(
        build_invoice(
            customer, subscription, plan.price_monthly, InvoiceStatus.PAID,
            CURRENT_PERIOD_START, CURRENT_PERIOD_START + timedelta(days=14),
        )
    )
    session.add(build_api_key(customer, plan.api_rate_limit, last_used_at=utc(2026, 9, 20)))
    session.add(
        build_usage_record(
            customer, int(plan.api_rate_limit * 0.4), CURRENT_PERIOD_START, CURRENT_PERIOD_END
        )
    )
    return customer


def seed_duplicate_payment_customer(
    session: AsyncSession, organization: Organization, name: str, email: str, plan: Plan
) -> Customer:
    """A customer double-charged for the same billing period — critical Billing Agent bait."""
    customer, subscription = _base_customer_stack(session, organization, name, email, plan)
    session.add(build_entitlement(subscription, plan, last_synced_at=utc(2026, 9, 1)))
    for hour in (2, 3):
        session.add(
            build_payment(
                customer, subscription, plan.price_monthly, PaymentStatus.SUCCEEDED,
                PaymentMethod.CARD, utc(2026, 9, 1, hour), CURRENT_PERIOD_START, CURRENT_PERIOD_END,
            )
        )
    session.add(
        build_invoice(
            customer, subscription, plan.price_monthly, InvoiceStatus.PAID,
            CURRENT_PERIOD_START, CURRENT_PERIOD_START + timedelta(days=14),
        )
    )
    session.add(build_api_key(customer, plan.api_rate_limit, last_used_at=utc(2026, 9, 19)))
    session.add(
        build_usage_record(
            customer, int(plan.api_rate_limit * 0.3), CURRENT_PERIOD_START, CURRENT_PERIOD_END
        )
    )
    return customer


def seed_failed_payment_customer(
    session: AsyncSession, organization: Organization, name: str, email: str, plan: Plan
) -> Customer:
    """A customer whose most recent payment failed; invoice remains open/overdue."""
    customer, subscription = _base_customer_stack(
        session, organization, name, email, plan, SubscriptionStatus.PAST_DUE
    )
    session.add(build_entitlement(subscription, plan, last_synced_at=utc(2026, 9, 1)))
    session.add(
        build_payment(
            customer, subscription, plan.price_monthly, PaymentStatus.FAILED,
            PaymentMethod.CARD, CURRENT_PERIOD_START, CURRENT_PERIOD_START, CURRENT_PERIOD_END,
        )
    )
    session.add(
        build_invoice(
            customer, subscription, plan.price_monthly, InvoiceStatus.OVERDUE,
            CURRENT_PERIOD_START, CURRENT_PERIOD_START + timedelta(days=7),
        )
    )
    session.add(build_api_key(customer, plan.api_rate_limit, last_used_at=utc(2026, 9, 10)))
    session.add(
        build_usage_record(
            customer, int(plan.api_rate_limit * 0.1), CURRENT_PERIOD_START, CURRENT_PERIOD_END
        )
    )
    return customer


def seed_pending_payment_customer(
    session: AsyncSession, organization: Organization, name: str, email: str, plan: Plan
) -> Customer:
    """A customer whose payment for the current period is still pending (e.g. ACH clearing)."""
    customer, subscription = _base_customer_stack(session, organization, name, email, plan)
    session.add(build_entitlement(subscription, plan, last_synced_at=utc(2026, 9, 1)))
    session.add(
        build_payment(
            customer, subscription, plan.price_monthly, PaymentStatus.PENDING,
            PaymentMethod.ACH, CURRENT_PERIOD_START, CURRENT_PERIOD_START, CURRENT_PERIOD_END,
        )
    )
    session.add(
        build_invoice(
            customer, subscription, plan.price_monthly, InvoiceStatus.OPEN,
            CURRENT_PERIOD_START, CURRENT_PERIOD_START + timedelta(days=14),
        )
    )
    session.add(build_api_key(customer, plan.api_rate_limit, last_used_at=utc(2026, 9, 18)))
    session.add(
        build_usage_record(
            customer, int(plan.api_rate_limit * 0.35), CURRENT_PERIOD_START, CURRENT_PERIOD_END
        )
    )
    return customer


def seed_stale_entitlement_customer(
    session: AsyncSession,
    organization: Organization,
    name: str,
    email: str,
    subscribed_plan: Plan,
    stale_granted_plan: Plan,
) -> Customer:
    """Subscription says `subscribed_plan` (e.g. Pro) but the entitlement is still stuck on
    `stale_granted_plan` (e.g. Free) — the classic sync-lag bug the Account/Technical agents
    must detect in later phases.
    """
    customer, subscription = _base_customer_stack(
        session, organization, name, email, subscribed_plan
    )
    session.add(
        build_entitlement(subscription, stale_granted_plan, last_synced_at=utc(2026, 8, 1))
    )
    session.add(
        build_payment(
            customer, subscription, subscribed_plan.price_monthly, PaymentStatus.SUCCEEDED,
            PaymentMethod.CARD, CURRENT_PERIOD_START, CURRENT_PERIOD_START, CURRENT_PERIOD_END,
        )
    )
    session.add(
        build_invoice(
            customer, subscription, subscribed_plan.price_monthly, InvoiceStatus.PAID,
            CURRENT_PERIOD_START, CURRENT_PERIOD_START + timedelta(days=14),
        )
    )
    session.add(build_api_key(customer, stale_granted_plan.api_rate_limit, last_used_at=utc(2026, 9, 20)))
    session.add(
        build_usage_record(
            customer, int(stale_granted_plan.api_rate_limit * 0.9), CURRENT_PERIOD_START, CURRENT_PERIOD_END
        )
    )
    return customer


def seed_locked_account_customer(
    session: AsyncSession, organization: Organization, name: str, email: str, plan: Plan
) -> Customer:
    """A customer locked out after repeated failed logins."""
    customer = build_customer(organization, name, email, CustomerStatus.ACTIVE)
    account = build_account(
        customer,
        status=AccountStatus.LOCKED,
        failed_login_attempts=7,
        last_login_at=utc(2026, 9, 15, 9),
        last_login_ip="198.51.100.23",
    )
    subscription = build_subscription(
        customer, plan, SubscriptionStatus.ACTIVE, date(2026, 2, 1), date(2026, 11, 1)
    )
    session.add_all([customer, account, subscription])
    session.add(build_entitlement(subscription, plan, last_synced_at=utc(2026, 9, 1)))
    session.add(
        build_payment(
            customer, subscription, plan.price_monthly, PaymentStatus.SUCCEEDED,
            PaymentMethod.CARD, CURRENT_PERIOD_START, CURRENT_PERIOD_START, CURRENT_PERIOD_END,
        )
    )
    session.add(build_api_key(customer, plan.api_rate_limit, status=ApiKeyStatus.ACTIVE))
    return customer


def seed_false_positive_high_usage_customer(
    session: AsyncSession, organization: Organization, name: str, email: str, plan: Plan
) -> Customer:
    """A customer using ~95% of a *large* Enterprise-level quota: unusual-looking but
    entirely legitimate — future agents must not auto-escalate this as abuse/fraud.
    """
    customer, subscription = _base_customer_stack(session, organization, name, email, plan)
    session.add(build_entitlement(subscription, plan, last_synced_at=utc(2026, 9, 1)))
    session.add(
        build_payment(
            customer, subscription, plan.price_monthly, PaymentStatus.SUCCEEDED,
            PaymentMethod.WIRE, CURRENT_PERIOD_START, CURRENT_PERIOD_START, CURRENT_PERIOD_END,
        )
    )
    session.add(
        build_invoice(
            customer, subscription, plan.price_monthly, InvoiceStatus.PAID,
            CURRENT_PERIOD_START, CURRENT_PERIOD_START + timedelta(days=30),
        )
    )
    session.add(build_api_key(customer, plan.api_rate_limit, last_used_at=utc(2026, 9, 21)))
    session.add(
        build_usage_record(
            customer, int(plan.api_rate_limit * 0.95), CURRENT_PERIOD_START, CURRENT_PERIOD_END
        )
    )
    return customer

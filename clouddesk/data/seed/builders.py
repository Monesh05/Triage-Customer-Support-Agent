# builders.py
# Purpose: Small factory functions that build (but do not persist) individual CloudDesk ORM
#          instances for the seed script. Keeping construction logic here keeps seed.py
#          focused on orchestration/scenario composition (org coding standard: functions <=40
#          lines, one responsibility each).
# Author: CloudDesk Team
# Date: 2026-09-21

import hashlib
import secrets
import uuid
from datetime import date, datetime, timezone

from app.models.account import Account
from app.models.api_key import ApiKey
from app.models.customer import Customer
from app.models.enums import (
    AccountStatus,
    ApiKeyStatus,
    CustomerStatus,
    IncidentSeverity,
    IncidentStatus,
    InvoiceStatus,
    PaymentMethod,
    PaymentStatus,
    SubscriptionStatus,
    TicketPriority,
    TicketStatus,
)
from app.models.incident import ServiceIncident
from app.models.invoice import Invoice
from app.models.organization import Organization
from app.models.payment import Payment
from app.models.plan import Plan
from app.models.subscription import Entitlement, Subscription
from app.models.ticket import SupportTicket
from app.models.usage import UsageRecord


def utc(year: int, month: int, day: int, hour: int = 0) -> datetime:
    """Build a UTC-aware datetime, used to keep seed timestamps deterministic."""
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


def build_organization(name: str, domain: str) -> Organization:
    return Organization(name=name, domain=domain)


def build_plan(name: str, price_monthly: float, api_rate_limit: int, features: list[str]) -> Plan:
    return Plan(
        name=name,
        price_monthly=price_monthly,
        api_rate_limit=api_rate_limit,
        features=features,
    )


def build_customer(
    organization: Organization, name: str, email: str, status: CustomerStatus
) -> Customer:
    return Customer(organization=organization, name=name, email=email, status=status)


def build_account(
    customer: Customer,
    status: AccountStatus = AccountStatus.ACTIVE,
    mfa_enabled: bool = True,
    failed_login_attempts: int = 0,
    last_login_at: datetime | None = None,
    last_login_ip: str | None = "203.0.113.10",
    permissions: list[str] | None = None,
) -> Account:
    return Account(
        customer=customer,
        status=status,
        mfa_enabled=mfa_enabled,
        failed_login_attempts=failed_login_attempts,
        last_login_at=last_login_at,
        last_login_ip=last_login_ip,
        permissions=permissions if permissions is not None else ["read", "write"],
    )


def build_subscription(
    customer: Customer,
    plan: Plan,
    status: SubscriptionStatus,
    start_date: date,
    renewal_date: date,
) -> Subscription:
    return Subscription(
        customer=customer,
        plan=plan,
        status=status,
        start_date=start_date,
        renewal_date=renewal_date,
    )


def build_entitlement(
    subscription: Subscription, granted_plan: Plan, last_synced_at: datetime
) -> Entitlement:
    return Entitlement(
        subscription=subscription,
        granted_plan_id=granted_plan.id,
        granted_plan=granted_plan,
        granted_api_rate_limit=granted_plan.api_rate_limit,
        granted_features=list(granted_plan.features),
        last_synced_at=last_synced_at,
    )


def build_payment(
    customer: Customer,
    subscription: Subscription,
    amount: float,
    status: PaymentStatus,
    method: PaymentMethod,
    created_at: datetime,
    period_start: datetime,
    period_end: datetime,
) -> Payment:
    return Payment(
        customer=customer,
        subscription=subscription,
        amount=amount,
        currency="USD",
        status=status,
        payment_method=method,
        created_at=created_at,
        transaction_reference=f"TXN_{uuid.uuid4().hex[:16].upper()}",
        billing_period_start=period_start,
        billing_period_end=period_end,
    )


def build_invoice(
    customer: Customer,
    subscription: Subscription,
    amount: float,
    status: InvoiceStatus,
    issued_at: datetime,
    due_at: datetime,
) -> Invoice:
    return Invoice(
        customer=customer,
        subscription=subscription,
        amount=amount,
        status=status,
        issued_at=issued_at,
        due_at=due_at,
    )


def build_api_key(
    customer: Customer,
    rate_limit: int,
    status: ApiKeyStatus = ApiKeyStatus.ACTIVE,
    last_used_at: datetime | None = None,
) -> ApiKey:
    """Build an API key record. The raw secret is generated, hashed, and discarded — only
    the hash is ever persisted, matching the "never expose raw API secrets" requirement.
    """
    raw_secret = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_secret.encode("utf-8")).hexdigest()
    return ApiKey(
        customer=customer,
        key_hash=key_hash,
        status=status,
        last_used_at=last_used_at,
        rate_limit=rate_limit,
    )


def build_usage_record(
    customer: Customer, api_calls: int, period_start: datetime, period_end: datetime
) -> UsageRecord:
    return UsageRecord(
        customer=customer,
        api_calls=api_calls,
        period_start=period_start,
        period_end=period_end,
    )


def build_incident(
    service_name: str,
    status: IncidentStatus,
    severity: IncidentSeverity,
    started_at: datetime,
    description: str,
    resolved_at: datetime | None = None,
) -> ServiceIncident:
    return ServiceIncident(
        service_name=service_name,
        status=status,
        severity=severity,
        started_at=started_at,
        resolved_at=resolved_at,
        description=description,
    )


def build_ticket(
    customer: Customer,
    subject: str,
    description: str,
    status: TicketStatus,
    priority: TicketPriority,
    assigned_to: str | None = None,
) -> SupportTicket:
    return SupportTicket(
        customer=customer,
        subject=subject,
        description=description,
        status=status,
        priority=priority,
        assigned_to=assigned_to,
    )

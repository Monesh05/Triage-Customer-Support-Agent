# tests/factories.py
# Purpose: Minimal test-only factory helpers for constructing a valid customer graph
#          (organization -> customer -> account/subscription/entitlement) without pulling in
#          the full seed script, so unit/integration tests stay fast and self-contained.
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid
from datetime import date, datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.customer import Customer
from app.models.enums import (
    AccountStatus,
    CustomerStatus,
    PaymentMethod,
    PaymentStatus,
    SubscriptionStatus,
)
from app.models.organization import Organization
from app.models.payment import Payment
from app.models.plan import Plan
from app.models.subscription import Entitlement, Subscription


async def create_org_and_plan(session: AsyncSession) -> tuple[Organization, Plan, Plan]:
    """Create a fresh organization plus Free and Pro plans, flushed so ids are assigned."""
    unique = uuid.uuid4().hex[:8]
    org = Organization(name=f"Test Org {unique}", domain=f"{unique}.test")
    free = Plan(name=f"Free-{unique}", price_monthly=0, api_rate_limit=1000, features=["basic"])
    pro = Plan(name=f"Pro-{unique}", price_monthly=49, api_rate_limit=50_000, features=["api_access"])
    session.add_all([org, free, pro])
    await session.flush()
    return org, free, pro


async def create_customer_with_account(
    session: AsyncSession,
    org: Organization,
    plan: Plan,
    account_status: AccountStatus = AccountStatus.ACTIVE,
    failed_login_attempts: int = 0,
) -> Customer:
    unique = uuid.uuid4().hex[:8]
    customer = Customer(
        organization=org, name=f"Test Customer {unique}",
        email=f"{unique}@test.example", status=CustomerStatus.ACTIVE,
    )
    account = Account(
        customer=customer, status=account_status,
        failed_login_attempts=failed_login_attempts, permissions=["read"],
    )
    subscription = Subscription(
        customer=customer, plan=plan, status=SubscriptionStatus.ACTIVE,
        start_date=date(2026, 1, 1), renewal_date=date(2026, 12, 1),
    )
    session.add_all([customer, account, subscription])
    await session.flush()
    session.add(
        Entitlement(
            subscription=subscription, granted_plan_id=plan.id,
            granted_api_rate_limit=plan.api_rate_limit,
            granted_features=list(plan.features),
            last_synced_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        )
    )
    await session.flush()
    return customer


async def create_payment(
    session: AsyncSession,
    customer: Customer,
    subscription_id: uuid.UUID,
    amount: float,
    status: PaymentStatus,
    created_at: datetime,
) -> Payment:
    payment = Payment(
        customer=customer, subscription_id=subscription_id, amount=amount,
        currency="USD", status=status, payment_method=PaymentMethod.CARD,
        created_at=created_at, transaction_reference=f"TXN_{uuid.uuid4().hex[:12]}",
        billing_period_start=created_at, billing_period_end=created_at,
    )
    session.add(payment)
    await session.flush()
    return payment

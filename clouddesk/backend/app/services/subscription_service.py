# app/services/subscription_service.py
# Purpose: Business logic for subscription retrieval and entitlement refresh. The refresh
#          operation re-syncs a subscription's Entitlement row to match its current Plan,
#          resolving the "Pro subscription but stale Free entitlement" scenario (spec
#          sections 6, 11, 19).
# Author: CloudDesk Team
# Date: 2026-09-21

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.base import utcnow
from app.models.enums import AuditActionType
from app.models.subscription import Entitlement, Subscription
from app.services.audit_service import record_audit
from app.services.exceptions import NotFoundError

logger = logging.getLogger(__name__)


async def get_subscriptions_by_customer(
    session: AsyncSession, customer_id: uuid.UUID
) -> list[Subscription]:
    """Fetch all subscriptions for a customer, with plan and entitlement eager-loaded."""
    result = await session.execute(
        select(Subscription)
        .where(Subscription.customer_id == customer_id)
        .options(
            selectinload(Subscription.plan),
            selectinload(Subscription.entitlement),
        )
        .order_by(Subscription.start_date.desc())
    )
    subscriptions = list(result.scalars().all())
    if not subscriptions:
        raise NotFoundError(f"No subscriptions found for customer {customer_id}")
    return subscriptions


def is_entitlement_stale(subscription: Subscription) -> bool:
    """An entitlement is stale if its granted plan no longer matches the subscription's plan."""
    if subscription.entitlement is None:
        return True
    return subscription.entitlement.granted_plan_id != subscription.plan_id


def _sync_entitlement_to_plan(session: AsyncSession, subscription: Subscription) -> None:
    """Overwrite (or create) a subscription's entitlement so it matches its current plan."""
    plan = subscription.plan
    if subscription.entitlement is None:
        subscription.entitlement = Entitlement(
            subscription_id=subscription.id,
            granted_plan_id=plan.id,
            granted_api_rate_limit=plan.api_rate_limit,
            granted_features=list(plan.features),
            last_synced_at=utcnow(),
        )
        session.add(subscription.entitlement)
    else:
        subscription.entitlement.granted_plan_id = plan.id
        subscription.entitlement.granted_api_rate_limit = plan.api_rate_limit
        subscription.entitlement.granted_features = list(plan.features)
        subscription.entitlement.last_synced_at = utcnow()


async def refresh_entitlement(
    session: AsyncSession, customer_id: uuid.UUID, reason: str, actor: str
) -> tuple[Subscription, bool]:
    """Re-sync the entitlement of a customer's active-most subscription to its current plan.

    Returns the updated subscription and whether the entitlement had actually been stale.

    Raises:
        NotFoundError: if the customer has no subscriptions.
    """
    subscriptions = await get_subscriptions_by_customer(session, customer_id)
    subscription = subscriptions[0]
    was_stale = is_entitlement_stale(subscription)

    _sync_entitlement_to_plan(session, subscription)
    record_audit(
        session, customer_id, AuditActionType.ENTITLEMENT_REFRESH, actor,
        {"reason": reason, "subscription_id": str(subscription.id), "was_stale": was_stale},
    )

    try:
        await session.commit()
    except Exception:
        logger.exception("Failed to commit entitlement refresh for customer %s", customer_id)
        await session.rollback()
        raise

    await session.refresh(subscription, attribute_names=["entitlement"])
    logger.info("Entitlement refreshed for subscription %s (was_stale=%s)", subscription.id, was_stale)
    return subscription, was_stale

# app/services/policy_service.py
# Purpose: Business logic for support policy lookup (refund rules, cancellation rules, plan
#          upgrade behavior, account recovery rules, escalation rules), per spec section 5.
#          Backs the Phase 2 `get_billing_policy` tool. Reads only — policies are seeded data.
# Author: CloudDesk Team
# Date: 2026-09-21

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.policy import SupportPolicy
from app.services.exceptions import NotFoundError

logger = logging.getLogger(__name__)


async def get_policy_by_key(session: AsyncSession, policy_key: str) -> SupportPolicy:
    """Fetch a support policy by its unique key (e.g. 'refund_rules') or raise NotFoundError."""
    result = await session.execute(
        select(SupportPolicy).where(SupportPolicy.policy_key == policy_key)
    )
    policy = result.scalar_one_or_none()
    if policy is None:
        raise NotFoundError(f"Support policy '{policy_key}' not found")
    return policy

# app/services/usage_service.py
# Purpose: Business logic for API usage record retrieval.
# Author: CloudDesk Team
# Date: 2026-09-21

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usage import UsageRecord
from app.services.exceptions import NotFoundError

logger = logging.getLogger(__name__)


async def get_usage_by_customer(
    session: AsyncSession, customer_id: uuid.UUID
) -> list[UsageRecord]:
    """Fetch all usage records for a customer, most recent period first."""
    result = await session.execute(
        select(UsageRecord)
        .where(UsageRecord.customer_id == customer_id)
        .order_by(UsageRecord.period_start.desc())
    )
    records = list(result.scalars().all())
    if not records:
        raise NotFoundError(f"No usage records found for customer {customer_id}")
    return records

# app/services/api_key_service.py
# Purpose: Business logic for API key metadata retrieval. Never returns key_hash or any raw
#          secret material to callers (spec sections 5, 27).
# Author: CloudDesk Team
# Date: 2026-09-21

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import ApiKey
from app.services.exceptions import NotFoundError

logger = logging.getLogger(__name__)


async def get_api_keys_by_customer(
    session: AsyncSession, customer_id: uuid.UUID
) -> list[ApiKey]:
    """Fetch all API keys for a customer (metadata only; hashes never leave this layer)."""
    result = await session.execute(
        select(ApiKey)
        .where(ApiKey.customer_id == customer_id)
        .order_by(ApiKey.created_at.desc())
    )
    api_keys = list(result.scalars().all())
    if not api_keys:
        raise NotFoundError(f"No API keys found for customer {customer_id}")
    return api_keys

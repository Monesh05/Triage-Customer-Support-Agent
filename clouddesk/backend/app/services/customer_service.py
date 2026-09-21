# app/services/customer_service.py
# Purpose: Business logic for retrieving customer records.
# Author: CloudDesk Team
# Date: 2026-09-21

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.services.exceptions import NotFoundError

logger = logging.getLogger(__name__)


async def get_customer_by_id(session: AsyncSession, customer_id: uuid.UUID) -> Customer:
    """Fetch a customer by id or raise NotFoundError."""
    try:
        result = await session.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        customer = result.scalar_one_or_none()
    except Exception:
        logger.exception("Failed to query customer %s", customer_id)
        raise

    if customer is None:
        raise NotFoundError(f"Customer {customer_id} not found")
    return customer

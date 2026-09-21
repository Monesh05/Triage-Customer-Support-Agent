# app/services/invoice_service.py
# Purpose: Business logic for invoice retrieval.
# Author: CloudDesk Team
# Date: 2026-09-21

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import Invoice
from app.services.exceptions import NotFoundError

logger = logging.getLogger(__name__)


async def get_invoices_by_customer(
    session: AsyncSession, customer_id: uuid.UUID
) -> list[Invoice]:
    """Fetch all invoices for a customer, most recently issued first."""
    result = await session.execute(
        select(Invoice)
        .where(Invoice.customer_id == customer_id)
        .order_by(Invoice.issued_at.desc())
    )
    invoices = list(result.scalars().all())
    if not invoices:
        raise NotFoundError(f"No invoices found for customer {customer_id}")
    return invoices

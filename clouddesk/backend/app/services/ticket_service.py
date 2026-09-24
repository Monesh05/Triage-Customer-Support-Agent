# app/services/ticket_service.py
# Purpose: Business logic for support ticket retrieval and creation.
# Author: CloudDesk Team
# Date: 2026-09-21

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AuditActionType, TicketPriority
from app.models.ticket import SupportTicket
from app.services.audit_service import record_audit
from app.services.customer_service import get_customer_by_id
from app.services.exceptions import NotFoundError

logger = logging.getLogger(__name__)


async def get_ticket_by_id(session: AsyncSession, ticket_id: uuid.UUID) -> SupportTicket:
    """Fetch a support ticket by id or raise NotFoundError."""
    result = await session.execute(
        select(SupportTicket).where(SupportTicket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()
    if ticket is None:
        raise NotFoundError(f"Ticket {ticket_id} not found")
    return ticket


async def list_tickets_for_customer(session: AsyncSession, customer_id: uuid.UUID) -> list[SupportTicket]:
    """List a customer's support tickets, most recent first (spec sections 25/26: a frontend
    support-history view and the Support Console's per-customer ticket list).

    Raises:
        NotFoundError: if the customer does not exist.
    """
    await get_customer_by_id(session, customer_id)  # 404s early if the customer id is unknown.
    result = await session.execute(
        select(SupportTicket)
        .where(SupportTicket.customer_id == customer_id)
        .order_by(SupportTicket.created_at.desc())
    )
    return list(result.scalars().all())


async def create_ticket(
    session: AsyncSession,
    customer_id: uuid.UUID,
    subject: str,
    description: str,
    priority: TicketPriority,
    actor: str,
) -> SupportTicket:
    """Create a new support ticket for a customer.

    Raises:
        NotFoundError: if the customer does not exist.
    """
    await get_customer_by_id(session, customer_id)  # Validate customer exists.

    ticket = SupportTicket(
        customer_id=customer_id,
        subject=subject,
        description=description,
        priority=priority,
    )
    session.add(ticket)

    record_audit(
        session, customer_id, AuditActionType.TICKET_CREATED, actor,
        {"subject": subject, "priority": priority.value},
    )

    try:
        await session.commit()
    except Exception:
        logger.exception("Failed to commit ticket creation for customer %s", customer_id)
        await session.rollback()
        raise

    await session.refresh(ticket)
    logger.info("Ticket %s created for customer %s", ticket.id, customer_id)
    return ticket

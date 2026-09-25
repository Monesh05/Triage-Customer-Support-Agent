# app/services/ticket_service.py
# Purpose: Business logic for support ticket retrieval, creation, and (post-launch, 2026-09-25)
#          a customer closing their own ticket.
# Author: CloudDesk Team
# Date: 2026-09-25

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AuditActionType, TicketPriority, TicketStatus
from app.models.ticket import SupportTicket
from app.services.audit_service import record_audit
from app.services.customer_service import get_customer_by_id
from app.services.exceptions import InvalidStateError, NotFoundError

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


DEFAULT_TICKET_LIST_LIMIT: int = 200


async def list_all_tickets(session: AsyncSession, limit: int = DEFAULT_TICKET_LIST_LIMIT) -> list[SupportTicket]:
    """List support tickets across all customers, most recent first (spec section 26: the
    Support Console's Tickets list). Capped at `limit` rows — the console is an internal triage
    view, not a full export, so an unbounded query here would be an easy way to blow up memory
    as ticket volume grows.
    """
    result = await session.execute(
        select(SupportTicket).order_by(SupportTicket.created_at.desc()).limit(limit)
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


_TICKET_CLOSE_ACTOR: str = "api:tickets.close"


async def close_ticket(session: AsyncSession, ticket_id: uuid.UUID) -> SupportTicket:
    """Transition a ticket to CLOSED, at the request of its own customer (or staff acting on
    their behalf) — the caller's authorization (customer owns this ticket, or is staff) has
    already been enforced by the router before this is called.

    Raises:
        NotFoundError: if the ticket does not exist.
        InvalidStateError: if the ticket is already closed (409 — closing is not idempotent, so a
            second attempt is a genuine no-op error rather than silently succeeding again).
    """
    ticket = await get_ticket_by_id(session, ticket_id)
    if ticket.status == TicketStatus.CLOSED:
        raise InvalidStateError(f"Ticket {ticket_id} is already closed")

    ticket.status = TicketStatus.CLOSED
    record_audit(
        session, ticket.customer_id, AuditActionType.TICKET_CLOSED, _TICKET_CLOSE_ACTOR,
        {"ticket_id": str(ticket_id)},
    )

    try:
        await session.commit()
    except Exception:
        logger.exception("Failed to commit ticket close for ticket %s", ticket_id)
        await session.rollback()
        raise

    await session.refresh(ticket)
    logger.info("Ticket %s closed", ticket_id)
    return ticket

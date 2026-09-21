# app/models/ticket.py
# Purpose: SQLAlchemy ORM model for support tickets, per spec section 5.
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import TicketPriority, TicketStatus


class SupportTicket(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A customer support ticket."""

    __tablename__ = "support_tickets"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, name="ticket_status", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=TicketStatus.OPEN,
    )
    priority: Mapped[TicketPriority] = mapped_column(
        Enum(TicketPriority, name="ticket_priority", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=TicketPriority.MEDIUM,
    )
    assigned_to: Mapped[str | None] = mapped_column(String(150), nullable=True)

    customer: Mapped["Customer"] = relationship(back_populates="tickets")

# app/models/invoice.py
# Purpose: SQLAlchemy ORM model for invoices, per spec section 5.
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import InvoiceStatus


class Invoice(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A billing invoice issued to a customer for a subscription period."""

    __tablename__ = "invoices"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, name="invoice_status", values_callable=lambda obj: [e.value for e in obj]), nullable=False
    )
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    customer: Mapped["Customer"] = relationship(back_populates="invoices")
    subscription: Mapped["Subscription"] = relationship(back_populates="invoices")

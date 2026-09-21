# app/models/payment.py
# Purpose: SQLAlchemy ORM models for payments and refund requests, per spec section 5.
#          Multiple successful Payment rows for the same subscription/billing period are a
#          deliberate seed scenario for the future Billing Agent to detect (spec section 6).
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow
from app.models.enums import PaymentMethod, PaymentStatus, RefundRequestStatus


class Payment(UUIDPrimaryKeyMixin, Base):
    """A single payment attempt/transaction for a customer's subscription."""

    __tablename__ = "payments"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status", values_callable=lambda obj: [e.value for e in obj]), nullable=False
    )
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="payment_method", values_callable=lambda obj: [e.value for e in obj]), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    transaction_reference: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )
    billing_period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    billing_period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    customer: Mapped["Customer"] = relationship(back_populates="payments")
    subscription: Mapped["Subscription"] = relationship(back_populates="payments")
    refund_requests: Mapped[list["RefundRequest"]] = relationship(
        back_populates="payment", cascade="all, delete-orphan"
    )


class RefundRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A request to refund a specific payment, created by POST /refunds/request.

    Sensitive per spec section 22: refunds require human approval before execution.
    """

    __tablename__ = "refund_requests"

    payment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("payments.id", ondelete="CASCADE"), nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[RefundRequestStatus] = mapped_column(
        Enum(RefundRequestStatus, name="refund_request_status", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=RefundRequestStatus.PENDING_APPROVAL,
    )

    payment: Mapped["Payment"] = relationship(back_populates="refund_requests")
    customer: Mapped["Customer"] = relationship()

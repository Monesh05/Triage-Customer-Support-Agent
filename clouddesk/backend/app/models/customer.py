# app/models/customer.py
# Purpose: SQLAlchemy ORM model for customers (end users of CloudDesk), per spec section 5.
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import CustomerStatus


class Customer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A CloudDesk customer (end user) belonging to an organization."""

    __tablename__ = "customers"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[CustomerStatus] = mapped_column(
        Enum(CustomerStatus, name="customer_status", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=CustomerStatus.ACTIVE,
    )

    organization: Mapped["Organization"] = relationship(back_populates="customers")
    account: Mapped["Account"] = relationship(
        back_populates="customer", uselist=False, cascade="all, delete-orphan"
    )
    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )
    invoices: Mapped[list["Invoice"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )
    api_keys: Mapped[list["ApiKey"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )
    usage_records: Mapped[list["UsageRecord"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )
    tickets: Mapped[list["SupportTicket"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )

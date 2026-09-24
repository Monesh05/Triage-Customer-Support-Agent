# app/models/customer.py
# Purpose: SQLAlchemy ORM model for customers (end users of CloudDesk), per spec section 5.
#          Phase 10 (spec section 27) adds `password_hash` so a customer can authenticate via
#          POST /api/v1/auth/login; it is always a bcrypt hash (see app.core.security), never
#          plaintext, and is never included in any response schema (see app.schemas.customer).
# Author: CloudDesk Team
# Date: 2026-09-24

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
    # Bcrypt hash of the customer's login password (Phase 10). Nullable so older rows created
    # before this column existed do not break; such a customer simply cannot log in until a hash
    # is set. Never selected into a response schema (see CustomerResponse).
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

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

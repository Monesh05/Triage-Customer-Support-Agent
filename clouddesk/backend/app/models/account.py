# app/models/account.py
# Purpose: SQLAlchemy ORM model for customer accounts (login/security state), per spec section 5.
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AccountStatus


class Account(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Login/security state for a customer's account."""

    __tablename__ = "accounts"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    status: Mapped[AccountStatus] = mapped_column(
        Enum(AccountStatus, name="account_status", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=AccountStatus.ACTIVE,
    )
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_login_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    permissions: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )

    customer: Mapped["Customer"] = relationship(back_populates="account")

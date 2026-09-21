# app/models/usage.py
# Purpose: SQLAlchemy ORM model for API usage records per billing period, per spec section 5.
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UsageRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """API usage for a customer over a given period."""

    __tablename__ = "usage_records"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    api_calls: Mapped[int] = mapped_column(Integer, nullable=False)
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    customer: Mapped["Customer"] = relationship(back_populates="usage_records")

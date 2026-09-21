# app/models/api_key.py
# Purpose: SQLAlchemy ORM model for customer API keys. Only a salted hash of the raw
#          secret is ever persisted; raw key material must never be stored or returned
#          by any GET endpoint (spec sections 5, 27).
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ApiKeyStatus


class ApiKey(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An API key issued to a customer. Only `key_hash` is stored, never the raw secret."""

    __tablename__ = "api_keys"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    key_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    status: Mapped[ApiKeyStatus] = mapped_column(
        Enum(ApiKeyStatus, name="api_key_status", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=ApiKeyStatus.ACTIVE,
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rate_limit: Mapped[int] = mapped_column(Integer, nullable=False)

    customer: Mapped["Customer"] = relationship(back_populates="api_keys")

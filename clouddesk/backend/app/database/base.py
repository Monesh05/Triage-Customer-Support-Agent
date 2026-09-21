# app/database/base.py
# Purpose: Declarative base class shared by all SQLAlchemy ORM models, plus a shared
#          mixin for id/timestamp columns used across CloudDesk domain tables.
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    """Return the current UTC timestamp (used as a default factory for timestamp columns)."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


class UUIDPrimaryKeyMixin:
    """Adds a UUID primary key column named `id` to a model."""

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, nullable=False
    )


class TimestampMixin:
    """Adds `created_at` / `updated_at` timestamp columns to a model."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

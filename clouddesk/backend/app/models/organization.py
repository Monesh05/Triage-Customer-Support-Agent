# app/models/organization.py
# Purpose: SQLAlchemy ORM model for organizations, the top-level tenant grouping customers.
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A tenant organization that one or more customers (users) belong to."""

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    domain: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)

    customers: Mapped[list["Customer"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )

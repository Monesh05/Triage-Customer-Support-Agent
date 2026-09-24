# app/models/staff_user.py
# Purpose: SQLAlchemy ORM model for internal CloudDesk support-console staff accounts (Phase 10,
#          spec section 27). Deliberately separate from `Customer`: staff are not tenants/end
#          users, they are internal operators who may act on ANY customer's data through the
#          approvals/traces/ticket-list endpoints, so a distinct table (rather than a boolean flag
#          on Customer) keeps that authorization boundary explicit at the schema level.
# Author: CloudDesk Team
# Date: 2026-09-24

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class StaffUser(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An internal CloudDesk support-console staff account."""

    __tablename__ = "staff_users"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    # Bcrypt hash (see app.core.security) of the staff member's login password. Never plaintext,
    # never returned by any response schema.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

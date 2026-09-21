# app/models/policy.py
# Purpose: SQLAlchemy ORM model for support policies (refund/cancellation/upgrade/
#          account-recovery/escalation rules), per spec section 5.
# Author: CloudDesk Team
# Date: 2026-09-21

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SupportPolicy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A named support policy (e.g. 'refund_rules') with structured rule data."""

    __tablename__ = "support_policies"

    policy_key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    rules: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

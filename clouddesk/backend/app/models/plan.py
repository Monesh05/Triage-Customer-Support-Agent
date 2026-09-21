# app/models/plan.py
# Purpose: SQLAlchemy ORM model for pricing plans (Free/Pro/Business/Enterprise).
# Author: CloudDesk Team
# Date: 2026-09-21

from sqlalchemy import Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Plan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A subscription pricing plan."""

    __tablename__ = "plans"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    price_monthly: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    api_rate_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    features: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="plan")

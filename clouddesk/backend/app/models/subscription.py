# app/models/subscription.py
# Purpose: SQLAlchemy ORM models for subscriptions and their entitlement snapshots.
#          The Entitlement model represents the *actually granted* API rate limit/features
#          for a customer, which can drift ("go stale") relative to the Subscription's plan —
#          this models the Pro-subscription-but-Free-entitlement mismatch scenario (spec section 6/11).
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow
from app.models.enums import SubscriptionStatus


class Subscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A customer's subscription to a plan."""

    __tablename__ = "subscriptions"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, name="subscription_status", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=SubscriptionStatus.ACTIVE,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    renewal_date: Mapped[date] = mapped_column(Date, nullable=False)

    customer: Mapped["Customer"] = relationship(back_populates="subscriptions")
    plan: Mapped["Plan"] = relationship(back_populates="subscriptions")
    payments: Mapped[list["Payment"]] = relationship(back_populates="subscription")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="subscription")
    entitlement: Mapped["Entitlement"] = relationship(
        back_populates="subscription", uselist=False, cascade="all, delete-orphan"
    )


class Entitlement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The actually-granted entitlement (rate limit/features) for a subscription.

    In a healthy state this mirrors `subscription.plan`. It can go stale after a plan
    change if the entitlement sync job/agent has not refreshed it yet, producing the
    "subscription says Pro but API entitlement is Free" scenario used by the Account
    and Technical agents in later phases.
    """

    __tablename__ = "entitlements"

    subscription_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    granted_plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False
    )
    granted_api_rate_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    granted_features: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    subscription: Mapped["Subscription"] = relationship(back_populates="entitlement")
    granted_plan: Mapped["Plan"] = relationship()

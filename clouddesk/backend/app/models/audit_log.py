# app/models/audit_log.py
# Purpose: SQLAlchemy ORM model for the audit log of sensitive actions (refunds, unlocks,
#          entitlement refreshes), per spec sections 5 and 27 (audit sensitive actions).
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AuditActionType


class AuditLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An immutable record of a sensitive action taken on behalf of a customer."""

    __tablename__ = "audit_logs"

    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"), nullable=True
    )
    action_type: Mapped[AuditActionType] = mapped_column(
        Enum(AuditActionType, name="audit_action_type", values_callable=lambda obj: [e.value for e in obj]), nullable=False
    )
    actor: Mapped[str] = mapped_column(String(150), nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

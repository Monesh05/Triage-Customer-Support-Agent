# app/models/approval.py
# Purpose: SQLAlchemy ORM model for `approval_requests` — the persistent, generic
#          human-in-the-loop approval record for any sensitive agent-recommended action (spec
#          section 22: refund, account unlock, subscription modification, security setting
#          changes, customer data changes). A row is created for every `RecommendedAction` with
#          `requires_approval=True` that any specialist agent surfaces (billing/account/
#          technical/product all share that schema shape — see app/agents/schemas.py), so the
#          approval mechanism is not billing/refund-specific even though refunds are the only
#          action type Phase 3's agents actually produce in practice today. `thread_id`
#          correlates this row to the paused LangGraph run (app/graph/graph.py) so approving or
#          rejecting it can resume that exact workflow. `refund_request_id` optionally links to
#          a concrete `refund_requests` row when the action is a real, already-created refund
#          request (see app/services/approval_service.py for how that link is established).
# Author: CloudDesk Team
# Date: 2026-09-24

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ApprovalStatus

MAX_AGENT_NAME_LENGTH: int = 50
MAX_ACTOR_NAME_LENGTH: int = 150


class ApprovalRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A pending (or decided) human-in-the-loop approval for one agent-recommended action."""

    __tablename__ = "approval_requests"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    thread_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(String(MAX_AGENT_NAME_LENGTH), nullable=False)
    action_description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus, name="approval_status", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=ApprovalStatus.PENDING,
    )
    decided_by: Mapped[str | None] = mapped_column(String(MAX_ACTOR_NAME_LENGTH), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    refund_request_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("refund_requests.id", ondelete="SET NULL"), nullable=True
    )

    customer: Mapped["Customer"] = relationship()
    refund_request: Mapped["RefundRequest | None"] = relationship()

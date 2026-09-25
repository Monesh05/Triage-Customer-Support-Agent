# app/models/conversation.py
# Purpose: SQLAlchemy ORM model for `conversation_records` — the persisted counterpart of the
#          Phase 9 in-process `ConversationRecord` registry (spec section 25) that
#          app.services.conversation_service used to keep purely in a module-level `dict`. That
#          registry does not survive a backend process restart, which was flagged as a known gap
#          in the Phase 5 and Phase 9 reports and in README's "Production Deployment" section;
#          this table closes it. One row per conversation started through
#          POST /api/v1/conversations, keyed by its LangGraph `thread_id`, updated in place as the
#          background workflow run progresses/pauses/completes/fails (see
#          app.services.conversation_service for the write/read paths and why a small mirrored
#          table was chosen over reconstructing this same information from the LangGraph
#          checkpoint + Phase 7 `AgentRun` rows on every poll).
# Author: CloudDesk Team
# Date: 2026-09-25

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow

MAX_THREAD_ID_LENGTH: int = 64
MAX_CUSTOMER_ID_LENGTH: int = 64
MAX_TICKET_ID_LENGTH: int = 36
MAX_STATUS_LENGTH: int = 20


class ConversationRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One customer-facing conversation's current status (spec section 25 polling state),
    durably persisted so `GET /api/v1/conversations/{thread_id}` keeps working across a backend
    restart for a conversation that is in progress, paused awaiting approval, or already
    completed.

    Field-by-field notes:
    - `thread_id` is the LangGraph checkpoint thread id (a UUID string) — unique per
      conversation, and the only key `GET /api/v1/conversations/{thread_id}` looks up by.
    - `customer_id` is stored as a plain string (not a `Uuid` FK) because some callers
      (tests, and any future non-customer-portal caller) legitimately use a non-UUID id here;
      this mirrors the same-typed field on the in-memory record it replaces.
    - `ticket_id` is nullable: the support-workflow run's best-effort ticket auto-creation
      (app.graph.graph._create_ticket_if_possible) can fail or be skipped for a non-UUID
      customer id, same as before.
    - `status` is the small closed vocabulary from
      `app.services.conversation_service.ConversationStatus`, stored as a plain string rather
      than a DB enum: it is written exclusively by this one service module (never reused by
      another table/feature the way e.g. `PaymentStatus` is), so a DB-level enum would only add
      migration friction for no real safety benefit here.
    """

    __tablename__ = "conversation_records"

    thread_id: Mapped[str] = mapped_column(String(MAX_THREAD_ID_LENGTH), nullable=False, unique=True, index=True)
    customer_id: Mapped[str] = mapped_column(String(MAX_CUSTOMER_ID_LENGTH), nullable=False, index=True)
    ticket_id: Mapped[str | None] = mapped_column(String(MAX_TICKET_ID_LENGTH), nullable=True)
    status: Mapped[str] = mapped_column(String(MAX_STATUS_LENGTH), nullable=False, default="in_progress")
    final_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

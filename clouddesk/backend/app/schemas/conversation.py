# app/schemas/conversation.py
# Purpose: Pydantic v2 schemas for the Phase 9 customer-facing chat API (spec section 25):
#          starting a support conversation and polling its live, safe high-level status. Distinct
#          from app.schemas.observability's AgentRunResponse/TicketTraceResponse, which are the
#          Support Console's full internal trace (spec section 26) — this module's `ConversationStep`
#          intentionally exposes only an agent name and a done/in_progress/failed marker, never
#          input/output summaries or tool calls, per spec section 25's "do not expose private
#          chain-of-thought" rule.
# Author: CloudDesk Team
# Date: 2026-09-24

import uuid
from typing import Literal

from pydantic import BaseModel, Field

MAX_MESSAGE_LENGTH: int = 5000
MAX_HISTORY_ENTRIES: int = 50

StepStatus = Literal["done", "in_progress", "failed"]
ConversationStatusValue = Literal["in_progress", "awaiting_approval", "completed", "escalated", "failed"]


class ConversationStartRequest(BaseModel):
    """Request body for starting a new customer support conversation."""

    customer_id: uuid.UUID
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)
    conversation_history: list[str] | None = Field(default=None, max_length=MAX_HISTORY_ENTRIES)


class ConversationStartResponse(BaseModel):
    """Immediate (202 Accepted) acknowledgement that a conversation's workflow run has started."""

    thread_id: str
    ticket_id: uuid.UUID | None
    status: ConversationStatusValue


class ConversationStep(BaseModel):
    """One safe, high-level step in the customer-facing "AI Support Team" progress display
    (spec section 25), e.g. `{"step": "Checking billing", "status": "done"}`."""

    step: str
    status: StepStatus


class ConversationStatusResponse(BaseModel):
    """Current status of a conversation, for the customer-facing chat UI to poll."""

    thread_id: str
    ticket_id: uuid.UUID | None
    status: ConversationStatusValue
    steps: list[ConversationStep]
    final_response: str | None

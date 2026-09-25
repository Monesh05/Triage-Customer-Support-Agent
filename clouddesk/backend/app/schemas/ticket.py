# app/schemas/ticket.py
# Purpose: Pydantic v2 schemas for support ticket resource, ticket-creation request, and (post-
#          launch, 2026-09-25) the customer-safe ticket outcome summary (spec section 25's
#          no-chain-of-thought rule) used by the new customer-facing ticket detail page.
# Author: CloudDesk Team
# Date: 2026-09-25

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from app.models.enums import TicketPriority, TicketStatus
from app.schemas.common import ORMModel

if TYPE_CHECKING:
    from app.models.conversation import ConversationRecord
    from app.models.ticket import SupportTicket


class SupportTicketCreate(BaseModel):
    customer_id: uuid.UUID
    subject: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=5000)
    priority: TicketPriority = TicketPriority.MEDIUM


class SupportTicketResponse(ORMModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    subject: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    created_at: datetime
    updated_at: datetime
    assigned_to: str | None


class TicketSummaryResponse(ORMModel):
    """A customer-safe outcome summary for one ticket (post-launch, 2026-09-25): the customer
    portal's ticket detail page uses this INSTEAD OF the staff-only `GET /tickets/{id}/trace`,
    which exposes raw specialist tool_calls/tool_results/reasoning (spec section 25's explicit
    no-chain-of-thought rule, already enforced for the live chat's `steps` in
    app.api.v1.conversations). The resolution text here is the same already-sanitized
    `ConversationRecord.final_response` the chat itself showed the customer while the run was in
    progress — never a re-derivation from the raw Agent Observability trace.
    """

    ticket_id: uuid.UUID
    subject: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    created_at: datetime
    escalated: bool
    resolution_message: str | None = Field(
        description="The safe, customer-facing outcome text, or None if the ticket's workflow "
        "has not produced one yet (e.g. still in progress, or a ticket created outside the chat)."
    )

    @classmethod
    def from_ticket_and_conversation(
        cls, ticket: "SupportTicket", conversation: "ConversationRecord | None"
    ) -> "TicketSummaryResponse":
        """Build the summary from a ticket row plus its most recent conversation record, if any."""
        escalated = conversation is not None and conversation.status == "escalated"
        return cls(
            ticket_id=ticket.id,
            subject=ticket.subject,
            description=ticket.description,
            status=ticket.status,
            priority=ticket.priority,
            created_at=ticket.created_at,
            escalated=escalated,
            resolution_message=conversation.final_response if conversation else None,
        )

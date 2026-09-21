# app/schemas/ticket.py
# Purpose: Pydantic v2 schemas for support ticket resource and ticket-creation request.
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import TicketPriority, TicketStatus
from app.schemas.common import ORMModel


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

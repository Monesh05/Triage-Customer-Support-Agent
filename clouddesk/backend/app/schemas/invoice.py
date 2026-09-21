# app/schemas/invoice.py
# Purpose: Pydantic v2 response schema for the Invoice resource.
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid
from datetime import datetime

from app.models.enums import InvoiceStatus
from app.schemas.common import ORMModel


class InvoiceResponse(ORMModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    subscription_id: uuid.UUID
    amount: float
    status: InvoiceStatus
    issued_at: datetime
    due_at: datetime

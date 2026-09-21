# app/schemas/usage.py
# Purpose: Pydantic v2 response schema for API usage records.
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid
from datetime import datetime

from app.schemas.common import ORMModel


class UsageRecordResponse(ORMModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    api_calls: int
    period_start: datetime
    period_end: datetime

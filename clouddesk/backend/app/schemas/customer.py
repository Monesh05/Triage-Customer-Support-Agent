# app/schemas/customer.py
# Purpose: Pydantic v2 response schema for the Customer resource.
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid
from datetime import datetime

from app.models.enums import CustomerStatus
from app.schemas.common import ORMModel


class CustomerResponse(ORMModel):
    id: uuid.UUID
    name: str
    email: str
    organization_id: uuid.UUID
    created_at: datetime
    status: CustomerStatus

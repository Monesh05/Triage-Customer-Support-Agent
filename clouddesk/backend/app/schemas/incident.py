# app/schemas/incident.py
# Purpose: Pydantic v2 response schema for service incidents.
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid
from datetime import datetime

from app.models.enums import IncidentSeverity, IncidentStatus
from app.schemas.common import ORMModel


class ServiceIncidentResponse(ORMModel):
    id: uuid.UUID
    service_name: str
    status: IncidentStatus
    severity: IncidentSeverity
    started_at: datetime
    resolved_at: datetime | None
    description: str

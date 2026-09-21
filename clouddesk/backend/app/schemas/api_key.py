# app/schemas/api_key.py
# Purpose: Pydantic v2 response schema for API keys. Deliberately omits `key_hash` and any
#          raw secret material — only status/last_used_at/rate_limit metadata is exposed,
#          per spec sections 5 and 27 ("never expose raw passwords/API keys").
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid
from datetime import datetime

from app.models.enums import ApiKeyStatus
from app.schemas.common import ORMModel


class ApiKeyResponse(ORMModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    status: ApiKeyStatus
    created_at: datetime
    last_used_at: datetime | None
    rate_limit: int

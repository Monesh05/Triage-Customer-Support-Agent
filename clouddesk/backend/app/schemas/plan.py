# app/schemas/plan.py
# Purpose: Pydantic v2 response schema for the Plan resource.
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid

from app.schemas.common import ORMModel


class PlanResponse(ORMModel):
    id: uuid.UUID
    name: str
    price_monthly: float
    api_rate_limit: int
    features: list[str]

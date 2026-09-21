# app/schemas/subscription.py
# Purpose: Pydantic v2 schemas for Subscription/Entitlement resources and the
#          entitlements/refresh request/response.
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.enums import SubscriptionStatus
from app.schemas.common import ORMModel
from app.schemas.plan import PlanResponse


class EntitlementResponse(ORMModel):
    id: uuid.UUID
    subscription_id: uuid.UUID
    granted_plan_id: uuid.UUID
    granted_api_rate_limit: int
    granted_features: list[str]
    last_synced_at: datetime


class SubscriptionResponse(ORMModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    plan_id: uuid.UUID
    status: SubscriptionStatus
    start_date: date
    renewal_date: date
    plan: PlanResponse
    entitlement: EntitlementResponse | None = None


class EntitlementRefreshRequest(BaseModel):
    customer_id: uuid.UUID
    reason: str = Field(default="manual_refresh", max_length=200)


class EntitlementRefreshResponse(BaseModel):
    subscription_id: uuid.UUID
    was_stale: bool
    entitlement: EntitlementResponse
    message: str

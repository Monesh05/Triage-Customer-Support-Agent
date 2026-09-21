# app/schemas/payment.py
# Purpose: Pydantic v2 schemas for Payment resources and the refund-request request/response.
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import PaymentMethod, PaymentStatus, RefundRequestStatus
from app.schemas.common import ORMModel


class PaymentResponse(ORMModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    subscription_id: uuid.UUID
    amount: float
    currency: str
    status: PaymentStatus
    payment_method: PaymentMethod
    created_at: datetime
    transaction_reference: str
    billing_period_start: datetime
    billing_period_end: datetime


class RefundRequestCreate(BaseModel):
    payment_id: uuid.UUID
    reason: str = Field(min_length=1, max_length=1000)


class RefundRequestResponse(ORMModel):
    id: uuid.UUID
    payment_id: uuid.UUID
    customer_id: uuid.UUID
    amount: float
    reason: str
    status: RefundRequestStatus
    created_at: datetime

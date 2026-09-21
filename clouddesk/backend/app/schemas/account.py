# app/schemas/account.py
# Purpose: Pydantic v2 schemas for the Account resource and account-unlock request/response.
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import AccountStatus
from app.schemas.common import ORMModel


class AccountResponse(ORMModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    status: AccountStatus
    mfa_enabled: bool
    failed_login_attempts: int
    last_login_at: datetime | None
    last_login_ip: str | None
    permissions: list[str]


class AccountUnlockRequest(BaseModel):
    customer_id: uuid.UUID
    reason: str = Field(min_length=1, max_length=500)


class AccountUnlockResponse(BaseModel):
    account_id: uuid.UUID
    status: AccountStatus
    failed_login_attempts: int
    message: str

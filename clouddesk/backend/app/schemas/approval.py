# app/schemas/approval.py
# Purpose: Pydantic v2 schemas for the human-in-the-loop approval API (spec sections 7, 22, 26):
#          listing/reading approval requests and the approve/reject request/response bodies.
# Author: CloudDesk Team
# Date: 2026-09-24

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import ApprovalStatus
from app.schemas.common import ORMModel

MAX_REJECTION_REASON_LENGTH: int = 1000
DEFAULT_ACTOR: str = "support_console"


class ApprovalRequestResponse(ORMModel):
    """One pending or decided human-approval action (spec section 26's Approval Queue)."""

    id: uuid.UUID
    customer_id: uuid.UUID
    thread_id: str
    agent_name: str
    action_description: str
    amount: float | None
    payload: dict[str, Any]
    status: ApprovalStatus
    decided_by: str | None
    decided_at: datetime | None
    rejection_reason: str | None
    refund_request_id: uuid.UUID | None
    created_at: datetime


class ApprovalDecisionRequest(BaseModel):
    """Request body for approving/rejecting one pending action. `actor` identifies the human
    reviewer (e.g. a support-console user id); defaults to a generic actor when omitted so the
    endpoint stays usable before Phase 9's console UI exists.
    """

    actor: str = Field(default=DEFAULT_ACTOR, min_length=1, max_length=150)
    reason: str | None = Field(default=None, max_length=MAX_REJECTION_REASON_LENGTH)


class ApprovalDecisionResponse(BaseModel):
    """Result of an approve/reject decision: the updated approval record, whether a concrete
    side effect was actually executed, and the resumed workflow's outcome when available.
    """

    approval_request: ApprovalRequestResponse
    executed: bool
    workflow_resumed: bool
    final_response: str | None = None

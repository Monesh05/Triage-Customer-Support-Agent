# app/tools/schemas.py
# Purpose: Pydantic v2 data schemas returned inside ToolResult.data for the Phase 2 tool
#          layer. Tools reuse app/schemas/* response models wherever an existing Phase 1
#          schema already fits (e.g. CustomerResponse, PaymentResponse); this module only
#          defines the additional shapes those schemas don't cover.
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import AccountStatus, IncidentSeverity, IncidentStatus


class LoginHistoryData(BaseModel):
    """Login-security snapshot for an account.

    LIMITATION: Phase 1 has no dedicated login-history table. This reflects exactly the
    fields the `accounts` table stores (last attempt only), never fabricated history.
    """

    account_id: uuid.UUID
    customer_id: uuid.UUID
    last_login_at: datetime | None
    last_login_ip: str | None
    failed_login_attempts: int
    account_status: AccountStatus


class AccountPermissionsData(BaseModel):
    """The account's stored permission grants, verbatim."""

    account_id: uuid.UUID
    customer_id: uuid.UUID
    permissions: list[str]


class MfaStatusData(BaseModel):
    """Whether MFA is enabled for the account."""

    account_id: uuid.UUID
    customer_id: uuid.UUID
    mfa_enabled: bool


class ServiceStatusData(BaseModel):
    """Current status of one named service, derived from its most recent incident."""

    service_name: str
    status: IncidentStatus
    severity: IncidentSeverity | None
    is_operational: bool
    active_incident_id: uuid.UUID | None
    description: str | None


class ErrorLogEntryData(BaseModel):
    """A single (stubbed, in Phase 2) error-log entry. Reserved for a future real log store."""

    timestamp: datetime
    message: str


class ErrorLogSearchData(BaseModel):
    """Result of an error-log search.

    LIMITATION: Phase 1 has no error-log table. `not_implemented` is always True and
    `entries` is always empty in Phase 2 — this must never be treated as "no errors found".
    """

    query: str
    not_implemented: bool
    entries: list[ErrorLogEntryData]


class ProductDocMatchData(BaseModel):
    """A single product/feature keyword-search match."""

    product_id: uuid.UUID
    name: str
    description: str


class ProductDocSearchData(BaseModel):
    """Result of a product-doc search.

    NOTE: keyword (ILIKE) substring search over app.models.product.Product only. Semantic/
    vector search over a real documentation corpus (spec section 14, pgvector) is a later
    phase; this is not that.
    """

    query: str
    matches: list[ProductDocMatchData]


class BillingPolicyData(BaseModel):
    """A support policy record (refund/cancellation/upgrade/recovery/escalation rules)."""

    policy_key: str
    title: str
    description: str
    rules: dict[str, bool | int | float | str | list[str]]


class RefundCalculationData(BaseModel):
    """The refundable amount computed for a payment, without creating a refund request."""

    payment_id: uuid.UUID
    is_eligible: bool
    refundable_amount: float
    currency: str
    reason: str


class RefundRequestData(BaseModel):
    """A created refund request. Always PENDING_APPROVAL — a tool never marks a refund done."""

    id: uuid.UUID
    payment_id: uuid.UUID
    customer_id: uuid.UUID
    amount: float
    reason: str
    status: str
    created_at: datetime


class EntitlementRefreshData(BaseModel):
    """Result of refreshing a subscription's entitlement to match its current plan."""

    subscription_id: uuid.UUID
    was_stale: bool
    granted_plan_id: uuid.UUID
    granted_api_rate_limit: int
    granted_features: list[str]

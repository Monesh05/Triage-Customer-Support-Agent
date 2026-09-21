# app/models/enums.py
# Purpose: Central definitions of all domain enums used by CloudDesk ORM models and
#          Pydantic schemas (status/severity/priority fields), per spec section 5.
# Author: CloudDesk Team
# Date: 2026-09-21

import enum


class CustomerStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CHURNED = "churned"


class AccountStatus(str, enum.Enum):
    ACTIVE = "active"
    LOCKED = "locked"
    DISABLED = "disabled"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELED = "canceled"


class PaymentStatus(str, enum.Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PENDING = "pending"
    REFUNDED = "refunded"


class PaymentMethod(str, enum.Enum):
    CARD = "card"
    ACH = "ach"
    PAYPAL = "paypal"
    WIRE = "wire"


class InvoiceStatus(str, enum.Enum):
    PAID = "paid"
    OPEN = "open"
    OVERDUE = "overdue"
    VOID = "void"


class ApiKeyStatus(str, enum.Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class IncidentStatus(str, enum.Enum):
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MONITORING = "monitoring"
    RESOLVED = "resolved"


class IncidentSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING_CUSTOMER = "pending_customer"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class RefundRequestStatus(str, enum.Enum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"


class AuditActionType(str, enum.Enum):
    ACCOUNT_UNLOCK = "account_unlock"
    REFUND_REQUEST_CREATED = "refund_request_created"
    REFUND_REQUEST_APPROVED = "refund_request_approved"
    ENTITLEMENT_REFRESH = "entitlement_refresh"
    TICKET_CREATED = "ticket_created"

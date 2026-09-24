# app/models/__init__.py
# Purpose: Imports every ORM model module so that (a) SQLAlchemy's declarative registry can
#          resolve relationship() string references across files, and (b) Alembic's
#          `target_metadata = Base.metadata` sees every table for autogeneration.
# Author: CloudDesk Team
# Date: 2026-09-24

from app.database.base import Base
from app.models.account import Account
from app.models.api_key import ApiKey
from app.models.approval import ApprovalRequest
from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.incident import ServiceIncident
from app.models.invoice import Invoice
from app.models.organization import Organization
from app.models.payment import Payment, RefundRequest
from app.models.plan import Plan
from app.models.policy import SupportPolicy
from app.models.product import Product
from app.models.subscription import Entitlement, Subscription
from app.models.ticket import SupportTicket
from app.models.usage import UsageRecord

__all__ = [
    "Base",
    "Account",
    "ApiKey",
    "ApprovalRequest",
    "AuditLog",
    "Customer",
    "ServiceIncident",
    "Invoice",
    "Organization",
    "Payment",
    "RefundRequest",
    "Plan",
    "SupportPolicy",
    "Product",
    "Entitlement",
    "Subscription",
    "SupportTicket",
    "UsageRecord",
]

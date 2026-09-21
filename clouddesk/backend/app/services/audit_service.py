# app/services/audit_service.py
# Purpose: Small shared helper for recording sensitive-action audit log entries, used by
#          every service that performs a sensitive operation (spec sections 5, 27).
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.enums import AuditActionType


def record_audit(
    session: AsyncSession,
    customer_id: uuid.UUID | None,
    action_type: AuditActionType,
    actor: str,
    details: dict[str, str | bool],
) -> None:
    """Stage an AuditLog row on the given session (caller is responsible for commit)."""
    session.add(
        AuditLog(
            customer_id=customer_id,
            action_type=action_type,
            actor=actor,
            details=details,
        )
    )

# app/tools/technical.py
# Purpose: Technical Support Agent tool layer (spec section 12): API usage, API key status
#          (never exposes raw keys/hashes), service status, incidents, and error-log search.
#          Each function opens its own session via app.database.session.get_session() and
#          delegates to app.services.* — no raw SQL, no direct DB access.
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid

from app.database.session import get_session
from app.models.incident import ServiceIncident
from app.models.enums import IncidentStatus
from app.schemas.api_key import ApiKeyResponse
from app.schemas.incident import ServiceIncidentResponse
from app.schemas.usage import UsageRecordResponse
from app.services import api_key_service, incident_service, usage_service
from app.services.exceptions import NotFoundError
from app.tools.base import NOT_IMPLEMENTED_REASON, ToolInputError, ToolResult, parse_uuid
from app.tools.schemas import ErrorLogSearchData, ServiceStatusData

RESOLVED_STATUSES: frozenset[IncidentStatus] = frozenset({IncidentStatus.RESOLVED})


async def get_api_usage(customer_id: str | uuid.UUID) -> ToolResult[list[UsageRecordResponse]]:
    """Fetch a customer's API usage records, most recent period first."""
    try:
        cid = parse_uuid(customer_id, "customer_id")
        async with get_session() as session:
            records = await usage_service.get_usage_by_customer(session, cid)
            data = [UsageRecordResponse.model_validate(r) for r in records]
        return ToolResult(success=True, data=data)
    except (ToolInputError, NotFoundError) as exc:
        return ToolResult(success=False, error=str(exc))
    except Exception as exc:  # noqa: BLE001
        return ToolResult(success=False, error=f"Unexpected error in get_api_usage: {exc}")


async def get_api_key_status(customer_id: str | uuid.UUID) -> ToolResult[list[ApiKeyResponse]]:
    """Fetch a customer's API key metadata. NEVER includes key_hash or raw key material."""
    try:
        cid = parse_uuid(customer_id, "customer_id")
        async with get_session() as session:
            keys = await api_key_service.get_api_keys_by_customer(session, cid)
            data = [ApiKeyResponse.model_validate(k) for k in keys]
        return ToolResult(success=True, data=data)
    except (ToolInputError, NotFoundError) as exc:
        return ToolResult(success=False, error=str(exc))
    except Exception as exc:  # noqa: BLE001
        return ToolResult(success=False, error=f"Unexpected error in get_api_key_status: {exc}")


def _latest_relevant_incident(
    incidents: list[ServiceIncident], service_name: str
) -> ServiceIncident | None:
    """Return the most recent non-resolved incident for a service, else the most recent one."""
    for_service = [i for i in incidents if i.service_name == service_name]
    if not for_service:
        return None
    active = [i for i in for_service if i.status not in RESOLVED_STATUSES]
    return active[0] if active else for_service[0]


async def get_service_status(service_name: str) -> ToolResult[ServiceStatusData]:
    """Derive the current status of a named service from its most recent incident, if any."""
    try:
        async with get_session() as session:
            incidents = await incident_service.get_all_incidents(session)
            incident = _latest_relevant_incident(incidents, service_name)
            is_operational = incident is None or incident.status in RESOLVED_STATUSES
            data = ServiceStatusData(
                service_name=service_name,
                status=incident.status if incident else IncidentStatus.RESOLVED,
                severity=incident.severity if incident else None,
                is_operational=is_operational,
                active_incident_id=incident.id if incident and not is_operational else None,
                description=incident.description if incident else None,
            )
        return ToolResult(success=True, data=data)
    except Exception as exc:  # noqa: BLE001
        return ToolResult(success=False, error=f"Unexpected error in get_service_status: {exc}")


async def get_recent_incidents() -> ToolResult[list[ServiceIncidentResponse]]:
    """Fetch all service incidents, most recently started first."""
    try:
        async with get_session() as session:
            incidents = await incident_service.get_all_incidents(session)
            data = [ServiceIncidentResponse.model_validate(i) for i in incidents]
        return ToolResult(success=True, data=data)
    except Exception as exc:  # noqa: BLE001
        return ToolResult(success=False, error=f"Unexpected error in get_recent_incidents: {exc}")


async def search_error_logs(query: str) -> ToolResult[ErrorLogSearchData]:
    """Search application error logs for a query string.

    LIMITATION: Phase 1 has no error-log table/store. This always returns
    `not_implemented=True` with an empty result set — it must never be interpreted as
    "search ran and found nothing." A real log-backed implementation is a later phase.
    """
    data = ErrorLogSearchData(query=query, not_implemented=True, entries=[])
    return ToolResult(success=False, error=NOT_IMPLEMENTED_REASON, data=data)

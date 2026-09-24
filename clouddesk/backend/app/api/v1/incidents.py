# app/api/v1/incidents.py
# Purpose: REST endpoint for listing active/historical service incidents (spec section 7).
#          Phase 10 (spec section 27) security review: deliberately left UNauthenticated — this is
#          public service-status information (the same content a public status page would show),
#          contains no customer-specific or otherwise sensitive data, and every other real-world
#          status-page product (e.g. status.io-style pages) is intentionally public. Every other
#          endpoint in this API is customer- or staff-scoped; this is the one deliberate exception.
# Author: CloudDesk Team
# Date: 2026-09-21

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.schemas.incident import ServiceIncidentResponse
from app.services.incident_service import get_all_incidents

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_model=list[ServiceIncidentResponse])
async def read_incidents(
    session: AsyncSession = Depends(get_db_session),
) -> list[ServiceIncidentResponse]:
    """Return all service incidents, most recently started first."""
    incidents = await get_all_incidents(session)
    return [ServiceIncidentResponse.model_validate(i) for i in incidents]

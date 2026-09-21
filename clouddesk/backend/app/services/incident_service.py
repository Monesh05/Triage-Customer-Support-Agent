# app/services/incident_service.py
# Purpose: Business logic for service incident retrieval.
# Author: CloudDesk Team
# Date: 2026-09-21

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import ServiceIncident

logger = logging.getLogger(__name__)


async def get_all_incidents(session: AsyncSession) -> list[ServiceIncident]:
    """Fetch all service incidents, most recently started first."""
    result = await session.execute(
        select(ServiceIncident).order_by(ServiceIncident.started_at.desc())
    )
    return list(result.scalars().all())

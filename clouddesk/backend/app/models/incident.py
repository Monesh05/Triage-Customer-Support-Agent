# app/models/incident.py
# Purpose: SQLAlchemy ORM model for service incidents (API/Auth/Billing status), spec section 5/6.
# Author: CloudDesk Team
# Date: 2026-09-21

from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import IncidentSeverity, IncidentStatus


class ServiceIncident(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A service incident affecting one of CloudDesk's internal services."""

    __tablename__ = "service_incidents"

    service_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus, name="incident_status", values_callable=lambda obj: [e.value for e in obj]), nullable=False
    )
    severity: Mapped[IncidentSeverity] = mapped_column(
        Enum(IncidentSeverity, name="incident_severity", values_callable=lambda obj: [e.value for e in obj]), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)

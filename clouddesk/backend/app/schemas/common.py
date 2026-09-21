# app/schemas/common.py
# Purpose: Shared Pydantic v2 base classes/utilities used across CloudDesk response schemas.
# Author: CloudDesk Team
# Date: 2026-09-21

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    """Base class for response schemas built from SQLAlchemy ORM instances."""

    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseModel):
    """Standard structured error body returned by API error handlers."""

    detail: str

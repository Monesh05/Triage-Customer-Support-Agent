# app/services/exceptions.py
# Purpose: Typed exceptions raised by the service layer, translated into HTTP errors by
#          the API routers. Keeps the service layer framework-agnostic (no FastAPI imports).
# Author: CloudDesk Team
# Date: 2026-09-21


class ServiceError(Exception):
    """Base class for all service-layer errors."""


class NotFoundError(ServiceError):
    """Raised when a requested resource does not exist."""


class InvalidStateError(ServiceError):
    """Raised when an operation is not valid given the resource's current state."""

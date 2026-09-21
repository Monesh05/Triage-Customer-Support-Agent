# app/tools/base.py
# Purpose: Shared ToolResult wrapper, input-validation helpers, and tool-call audit logging
#          used by every module in app/tools/. Every tool function must catch Phase 1's
#          NotFoundError/InvalidStateError (and any unexpected exception) here and return a
#          ToolResult instead of letting a raw exception or ORM object escape (spec sections
#          8, 27; org rule A09: log mutating tool calls with customer id + action, never PII).
# Author: CloudDesk Team
# Date: 2026-09-21

import logging
import uuid
from typing import Generic, TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger("clouddesk.tools")

DataT = TypeVar("DataT")

NOT_IMPLEMENTED_REASON: str = "not_implemented_in_phase_2"


class ToolResult(BaseModel, Generic[DataT]):
    """Uniform structured result returned by every tool-layer function.

    Exactly one of `error`/`data` is meaningful depending on `success`. Agents (Phase 3+)
    should only trust `data` when `success` is True.
    """

    success: bool
    error: str | None = None
    data: DataT | None = None


class ToolInputError(Exception):
    """Raised when a tool receives an input that fails boundary validation."""


class _UUIDInput(BaseModel):
    """Internal helper model: validates a single value as a UUID."""

    value: uuid.UUID


def parse_uuid(raw: str | uuid.UUID, field_name: str) -> uuid.UUID:
    """Validate and coerce a raw identifier into a UUID.

    Raises:
        ToolInputError: if `raw` is not a valid UUID (e.g. malformed agent-supplied input).
    """
    try:
        return _UUIDInput(value=raw).value
    except ValidationError as exc:
        raise ToolInputError(f"Invalid {field_name}: {raw!r}") from exc


def log_tool_call(tool_name: str, customer_id: uuid.UUID | str | None, action: str) -> None:
    """Log a tool invocation for audit/observability. Never pass secrets or PII here."""
    logger.info("tool_call tool=%s customer_id=%s action=%s", tool_name, customer_id, action)

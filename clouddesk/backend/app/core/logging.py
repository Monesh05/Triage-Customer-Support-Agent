# app/core/logging.py
# Purpose: Configure structured application-wide logging (no print()/console.log usage).
#          Phase 10 (spec section 27; org policy "Every log: timestamp, request ID, operation,
#          outcome") adds the current request's id to every log line via a logging.Filter reading
#          app.core.middleware.request_id_var — no call site needs to pass a request id
#          explicitly, and a log line emitted outside any request (startup, a background task)
#          simply gets "-" for a request id.
# Author: CloudDesk Team
# Date: 2026-09-21

import logging
import sys

from app.core.config import get_settings
from app.core.middleware import request_id_var

_LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | request_id=%(request_id)s | %(name)s | %(message)s"
)


class _RequestIdFilter(logging.Filter):
    """Attach the current request's id (or "-" outside a request) to every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def configure_logging() -> None:
    """Configure the root logger once at application startup."""
    settings = get_settings()
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return  # Already configured (e.g. under pytest re-imports).

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    handler.addFilter(_RequestIdFilter())
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level.upper())

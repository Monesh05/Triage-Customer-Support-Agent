# app/core/logging.py
# Purpose: Configure structured application-wide logging (no print()/console.log usage).
# Author: CloudDesk Team
# Date: 2026-09-21

import logging
import sys

from app.core.config import get_settings

_LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)


def configure_logging() -> None:
    """Configure the root logger once at application startup."""
    settings = get_settings()
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return  # Already configured (e.g. under pytest re-imports).

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level.upper())

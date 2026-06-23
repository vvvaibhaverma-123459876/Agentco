"""
Civilization layer — Structured logging service.

All services use this for consistent JSON-formatted logs.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Optional


class StructuredLogger:
    """Structured JSON logger for civilization layer."""

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(name)
        self._setup_handler()

    def _setup_handler(self) -> None:
        """Setup JSON formatter."""
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)

        # Simple JSON formatter
        class JSONFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                log_data = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                }
                if record.exc_info:
                    log_data["exception"] = self.formatException(record.exc_info)
                return json.dumps(log_data)

        handler.setFormatter(JSONFormatter())
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)

    def info(self, message: str, **context) -> None:
        """Log info with context."""
        msg = f"{message}" + (f" | {json.dumps(context)}" if context else "")
        self.logger.info(msg)

    def error(self, message: str, **context) -> None:
        """Log error with context."""
        msg = f"{message}" + (f" | {json.dumps(context)}" if context else "")
        self.logger.error(msg)

    def warning(self, message: str, **context) -> None:
        """Log warning with context."""
        msg = f"{message}" + (f" | {json.dumps(context)}" if context else "")
        self.logger.warning(msg)

    def debug(self, message: str, **context) -> None:
        """Log debug with context."""
        msg = f"{message}" + (f" | {json.dumps(context)}" if context else "")
        self.logger.debug(msg)

    def exception(self, message: str, exc: Exception, **context) -> None:
        """Log exception with context."""
        context["exception_type"] = type(exc).__name__
        context["exception_message"] = str(exc)
        msg = f"{message} | {json.dumps(context)}"
        self.logger.error(msg, exc_info=exc)


def get_logger(name: str) -> StructuredLogger:
    """Get or create logger for a service."""
    return StructuredLogger(name)

"""Structured logging configuration for SageMCP.

Provides JSON-formatted structured logging with contextual fields
(tenant_slug, connector_id, request_id) via contextvars.
"""

import json
import logging
import sys
import time
from contextvars import ContextVar
from typing import Optional

# Context variables for request-scoped logging fields
_tenant_slug: ContextVar[Optional[str]] = ContextVar("tenant_slug", default=None)
_connector_id: ContextVar[Optional[str]] = ContextVar("connector_id", default=None)
_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def set_log_context(
    tenant_slug: Optional[str] = None,
    connector_id: Optional[str] = None,
    request_id: Optional[str] = None,
):
    """Set contextual logging fields for the current async context."""
    if tenant_slug is not None:
        _tenant_slug.set(tenant_slug)
    if connector_id is not None:
        _connector_id.set(connector_id)
    if request_id is not None:
        _request_id.set(request_id)


def clear_log_context():
    """Clear all contextual logging fields."""
    _tenant_slug.set(None)
    _connector_id.set(None)
    _request_id.set(None)


class StructuredFormatter(logging.Formatter):
    """JSON structured log formatter with context fields."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add context fields if present
        tenant = _tenant_slug.get()
        if tenant:
            log_entry["tenant_slug"] = tenant

        connector = _connector_id.get()
        if connector:
            log_entry["connector_id"] = connector

        request_id = _request_id.get()
        if request_id:
            log_entry["request_id"] = request_id

        # Add exception info if present
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


class HumanReadableFormatter(logging.Formatter):
    """Human-readable log formatter with context fields for development."""

    def format(self, record: logging.LogRecord) -> str:
        parts = [
            f"[{self.formatTime(record, self.datefmt)}]",
            f"{record.levelname:8s}",
            f"{record.name}:",
            record.getMessage(),
        ]

        # Add context fields if present
        ctx_parts = []
        tenant = _tenant_slug.get()
        if tenant:
            ctx_parts.append(f"tenant={tenant}")
        connector = _connector_id.get()
        if connector:
            ctx_parts.append(f"connector={connector}")
        request_id = _request_id.get()
        if request_id:
            ctx_parts.append(f"req={request_id}")

        if ctx_parts:
            parts.append(f"[{', '.join(ctx_parts)}]")

        msg = " ".join(parts)

        if record.exc_info and record.exc_info[1]:
            msg += "\n" + self.formatException(record.exc_info)

        return msg


def configure_logging(environment: str = "development", log_level: str = "INFO"):
    """Configure structured logging for the application.

    Args:
        environment: "production" for JSON output, anything else for human-readable.
        log_level: Logging level string (DEBUG, INFO, WARNING, ERROR).
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)

    if environment == "production":
        handler.setFormatter(StructuredFormatter())
    else:
        handler.setFormatter(HumanReadableFormatter(
            datefmt="%Y-%m-%d %H:%M:%S"
        ))

    root_logger.addHandler(handler)

    # Quiet noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

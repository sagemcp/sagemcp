"""Audit log model for tracking security-sensitive actions."""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from .base import Base


class ActorType(str, enum.Enum):
    """Type of actor performing the action."""

    USER = "user"
    API_KEY = "api_key"
    SYSTEM = "system"


class AuditLog(Base):
    """Immutable audit log entry for security-sensitive actions.

    Each row records a single action (e.g. tenant.create, connector.delete)
    with the actor, target resource, and request metadata.  Rows are
    append-only — no updates or deletes.
    """

    __tablename__ = "audit_logs"

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    # Who performed the action
    actor_id: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # What happened
    action: Mapped[str] = mapped_column(String(100), nullable=False)

    # What was acted on
    resource_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Tenant scope (nullable for platform-wide actions)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # Structured details (e.g. old/new values, extra context)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Request metadata
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    __table_args__ = (
        Index("ix_audit_logs_tenant_timestamp", "tenant_id", "timestamp"),
        Index("ix_audit_logs_action_timestamp", "action", "timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog(action='{self.action}', actor='{self.actor_id}', "
            f"resource='{self.resource_type}/{self.resource_id}')>"
        )

"""Generic connector-scoped MCP overrides."""

import uuid
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .connector import JSONType

if TYPE_CHECKING:
    from .connector import Connector


class ConnectorMCPOverride(Base):
    """Generic local override definition for connector MCP behavior."""

    __tablename__ = "connector_mcp_overrides"
    __table_args__ = (
        UniqueConstraint(
            "connector_id",
            "target_kind",
            "identifier",
            name="uq_connector_mcp_override_target_identifier",
        ),
    )

    connector_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("connectors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_kind: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    identifier: Mapped[str] = mapped_column(String(500), nullable=False)
    payload_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONType, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    connector: Mapped["Connector"] = relationship("Connector")

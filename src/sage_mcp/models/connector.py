"""Connector model for managing tenant-specific connector configurations."""

import enum
import json
import uuid
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class JSONType(TypeDecorator):
    """JSON type that handles serialization for SQLite and PostgreSQL."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Optional[Dict[str, Any]], dialect) -> Optional[str]:
        """Convert dict to JSON string before storing."""
        if value is not None:
            return json.dumps(value)
        return None

    def process_result_value(self, value: Optional[str], dialect) -> Optional[Dict[str, Any]]:
        """Convert JSON string back to dict after loading."""
        if value is not None:
            return json.loads(value)
        return None


if TYPE_CHECKING:
    from .tenant import Tenant
    from .connector_tool_state import ConnectorToolState


class ConnectorType(enum.Enum):
    """Supported connector types."""

    # Source control
    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"

    # Google Suite
    GOOGLE_DOCS = "google_docs"
    GOOGLE_CALENDAR = "google_calendar"
    GOOGLE_SHEETS = "google_sheets"
    GMAIL = "gmail"
    GOOGLE_SLIDES = "google_slides"

    # Documentation & knowledge
    NOTION = "notion"
    CONFLUENCE = "confluence"

    # Project management
    JIRA = "jira"
    LINEAR = "linear"

    # Communication
    SLACK = "slack"
    TEAMS = "teams"
    DISCORD = "discord"
    ZOOM = "zoom"

    # Microsoft Office
    OUTLOOK = "outlook"
    EXCEL = "excel"
    POWERPOINT = "powerpoint"

    # AI coding tools
    COPILOT = "copilot"
    CLAUDE_CODE = "claude_code"
    CODEX = "codex"
    CURSOR = "cursor"
    WINDSURF = "windsurf"

    # Custom / external
    CUSTOM = "custom"


class ConnectorRuntimeType(enum.Enum):
    """Runtime execution mode for connectors."""

    # In-process native Python connectors (current)
    NATIVE = "native"

    # External MCP servers via stdio
    EXTERNAL_PYTHON = "external_python"    # Python MCP SDK server
    EXTERNAL_NODEJS = "external_nodejs"    # Node.js @modelcontextprotocol/sdk
    EXTERNAL_GO = "external_go"            # Go MCP implementation
    EXTERNAL_CUSTOM = "external_custom"    # Any binary that speaks MCP over stdio


class Connector(Base):
    """Connector configuration for tenants."""

    __tablename__ = "connectors"

    # Foreign key to tenant
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Connector type
    connector_type: Mapped[ConnectorType] = mapped_column(
        Enum(
            ConnectorType,
            name="connectortype",
            create_constraint=False,
            native_enum=False,
            values_callable=lambda x: [e.value for e in x]
        ),
        nullable=False,
        index=True
    )

    # Display name for this connector instance
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Optional description
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Whether this connector is enabled
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Connector-specific configuration (JSON)
    configuration: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONType, nullable=True)

    # Runtime configuration for external MCP servers
    runtime_type: Mapped[ConnectorRuntimeType] = mapped_column(
        Enum(
            ConnectorRuntimeType,
            name="connectorruntimetype",
            create_constraint=False,
            native_enum=False,
            values_callable=lambda x: [e.value for e in x]
        ),
        nullable=False,
        default=ConnectorRuntimeType.NATIVE,
        server_default="native",
        index=True
    )

    # Command to execute for external MCP servers (JSON array, e.g., ["npx", "@modelcontextprotocol/server-github"])
    runtime_command: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Environment variables for external MCP servers (JSON object)
    runtime_env: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONType, nullable=True)

    # Working directory / package path for external MCP servers
    package_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="connectors")
    tool_states: Mapped[list["ConnectorToolState"]] = relationship(
        "ConnectorToolState",
        back_populates="connector",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Connector(type='{self.connector_type.value}', tenant_id='{self.tenant_id}')>"

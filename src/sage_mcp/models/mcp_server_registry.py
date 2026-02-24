"""Database models for MCP Server Registry."""

import enum
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, Enum, Integer, String, Text, TIMESTAMP, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SourceType(str, enum.Enum):
    """MCP server source types."""

    NPM = "npm"
    GITHUB = "github"
    CUSTOM = "custom"
    MANUAL = "manual"


class RuntimeType(str, enum.Enum):
    """MCP server runtime types."""

    NODEJS = "nodejs"
    PYTHON = "python"
    GO = "go"
    RUST = "rust"
    BINARY = "binary"


class MCPServerRegistry(Base):
    """Registry of discovered MCP servers from NPM, GitHub, and custom sources."""

    __tablename__ = "mcp_server_registry"

    # Basic information
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Discovery metadata
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, native_enum=False, create_constraint=False),
        nullable=False,
        index=True
    )
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    npm_package_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    github_repo: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Version tracking
    latest_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    available_versions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Protocol compatibility
    protocol_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    supported_protocols: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)

    # Server capabilities
    tools_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    resources_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    prompts_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Metadata from package.json / manifest
    manifest: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    readme: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Runtime requirements
    runtime_type: Mapped[RuntimeType] = mapped_column(
        Enum(RuntimeType, native_enum=False, create_constraint=False),
        nullable=False,
        index=True
    )
    runtime_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    dependencies: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # OAuth requirements
    requires_oauth: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    oauth_providers: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    oauth_scopes: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Container metadata
    docker_image: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    dockerfile_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    build_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Popularity & quality metrics
    download_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    star_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rating: Mapped[Optional[float]] = mapped_column(nullable=True)
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Publishing metadata
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    license: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    homepage_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    repository_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    documentation_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Discovery tracking
    first_discovered_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, default=datetime.utcnow, nullable=False
    )
    last_scanned_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)
    last_updated_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)

    # Status
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_deprecated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deprecation_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<MCPServerRegistry(name='{self.name}', source='{self.source_type}')>"


class JobStatus(str, enum.Enum):
    """Discovery job status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DiscoveryJob(Base):
    """Background discovery jobs for scanning NPM, GitHub, etc."""

    __tablename__ = "discovery_jobs"

    job_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, native_enum=False, create_constraint=False),
        default=JobStatus.PENDING,
        nullable=False,
        index=True
    )

    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, default=datetime.utcnow, nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)

    # Results
    servers_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    servers_added: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    servers_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<DiscoveryJob(type='{self.job_type}', status='{self.status}')>"


class InstallationStatus(str, enum.Enum):
    """MCP server installation status."""

    INSTALLING = "installing"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    UPDATING = "updating"


class MCPInstallation(Base):
    """Track MCP server installations per tenant."""

    __tablename__ = "mcp_installations"

    # Links
    registry_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    connector_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    # Installation metadata
    installed_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    installation_method: Mapped[str] = mapped_column(
        String(50), default="manual", nullable=False
    )

    # Container/Pod metadata
    docker_image_tag: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    container_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    pod_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Status
    status: Mapped[InstallationStatus] = mapped_column(
        Enum(InstallationStatus, native_enum=False, create_constraint=False),
        default=InstallationStatus.INSTALLING,
        nullable=False
    )

    # Timestamps
    installed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, default=datetime.utcnow, nullable=False
    )
    last_started_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)
    last_stopped_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)

    # Metrics
    total_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_errors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<MCPInstallation(connector_id='{self.connector_id}', status='{self.status}')>"

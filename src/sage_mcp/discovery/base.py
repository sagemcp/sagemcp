"""Base classes for MCP server discovery."""

from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel, Field


class MCPServerMetadata(BaseModel):
    """Discovered MCP server metadata."""

    name: str = Field(..., description="Server name/package name")
    display_name: Optional[str] = Field(None, description="Human-readable display name")
    description: Optional[str] = Field(None, description="Server description")

    # Source information
    source_type: str = Field(..., description="Source type: npm, github, custom")
    source_url: str = Field(..., description="Source URL or package URL")
    npm_package_name: Optional[str] = None
    github_repo: Optional[str] = None

    # Version information
    latest_version: Optional[str] = None
    available_versions: Optional[List[str]] = None

    # Runtime requirements
    runtime_type: str = Field("nodejs", description="Runtime: nodejs, python, go, etc.")
    runtime_version: Optional[str] = None

    # Protocol compatibility
    protocol_version: Optional[str] = None
    supported_protocols: Optional[List[str]] = None

    # Capabilities
    tools_count: int = 0
    resources_count: int = 0
    prompts_count: int = 0

    # Metadata
    manifest: Optional[dict] = None
    readme: Optional[str] = None

    # OAuth requirements
    requires_oauth: bool = False
    oauth_providers: List[str] = Field(default_factory=list)
    oauth_scopes: Optional[dict] = None

    # Popularity metrics
    star_count: int = 0
    download_count: int = 0

    # Publishing info
    author: Optional[str] = None
    license: Optional[str] = None
    homepage_url: Optional[str] = None
    repository_url: Optional[str] = None
    documentation_url: Optional[str] = None

    # Container information
    docker_image: Optional[str] = None
    dockerfile_url: Optional[str] = None

    class Config:
        """Pydantic config."""

        populate_by_name = True


class BaseDiscoveryProvider(ABC):
    """Base class for MCP server discovery providers."""

    @abstractmethod
    async def search(self, query: str = "", limit: int = 20) -> List[MCPServerMetadata]:
        """Search for MCP servers.

        Args:
            query: Search query string
            limit: Maximum results to return

        Returns:
            List of discovered MCP server metadata
        """
        pass

    @abstractmethod
    async def get_details(self, identifier: str) -> Optional[MCPServerMetadata]:
        """Get detailed metadata for a specific MCP server.

        Args:
            identifier: Package name, repo URL, etc.

        Returns:
            Detailed MCP server metadata or None if not found
        """
        pass

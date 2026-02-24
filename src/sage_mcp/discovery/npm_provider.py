"""NPM registry discovery provider for MCP servers."""

import httpx
import logging
from typing import List, Optional

from .base import BaseDiscoveryProvider, MCPServerMetadata

logger = logging.getLogger(__name__)


class NPMDiscoveryProvider(BaseDiscoveryProvider):
    """Discover MCP servers from NPM registry."""

    def __init__(self):
        """Initialize NPM discovery provider."""
        self.registry_url = "https://registry.npmjs.org"
        self.search_api = "https://registry.npmjs.com/-/v1/search"
        self.timeout = 30.0

    async def search(self, query: str = "", limit: int = 20) -> List[MCPServerMetadata]:
        """Search NPM for packages with 'mcp-server' keyword.

        Args:
            query: Additional search terms
            limit: Maximum results

        Returns:
            List of discovered MCP servers
        """
        servers = []

        async with httpx.AsyncClient() as client:
            try:
                # Build search query
                search_text = "keywords:mcp-server"
                if query:
                    search_text += f" {query}"

                params = {
                    "text": search_text,
                    "size": limit,
                    "quality": 0.4,
                    "popularity": 0.4,
                    "maintenance": 0.2
                }

                logger.info(f"Searching NPM with query: {search_text}")
                response = await client.get(
                    self.search_api,
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()

                logger.info(f"Found {len(data.get('objects', []))} NPM packages")

                for pkg_obj in data.get("objects", []):
                    package = pkg_obj.get("package", {})

                    # Validate it's an MCP server
                    keywords = package.get("keywords", [])
                    if "mcp-server" not in keywords and "model-context-protocol" not in keywords:
                        continue

                    # Get detailed information
                    metadata = await self.get_details(package["name"])
                    if metadata:
                        servers.append(metadata)

            except httpx.HTTPError as e:
                logger.error(f"NPM search failed: {e}")
            except Exception as e:
                logger.error(f"Error during NPM search: {e}")

        return servers

    async def get_details(self, package_name: str) -> Optional[MCPServerMetadata]:
        """Get detailed package information from NPM.

        Args:
            package_name: NPM package name

        Returns:
            MCPServerMetadata or None if fetch fails
        """
        async with httpx.AsyncClient() as client:
            try:
                # Fetch package metadata
                logger.debug(f"Fetching NPM package details: {package_name}")
                response = await client.get(
                    f"{self.registry_url}/{package_name}",
                    timeout=self.timeout
                )
                response.raise_for_status()
                pkg_data = response.json()

                # Get latest version info
                latest_version = pkg_data.get("dist-tags", {}).get("latest")
                if not latest_version:
                    logger.warning(f"No latest version found for {package_name}")
                    return None

                version_data = pkg_data.get("versions", {}).get(latest_version, {})

                # Extract MCP-specific metadata
                mcp_config = version_data.get("mcp", {})

                # Determine tools count
                tools_count = len(mcp_config.get("tools", []))
                if tools_count == 0:
                    # Try to estimate from description/keywords
                    tools_keywords = ["tool", "command", "function"]
                    description = pkg_data.get("description", "").lower()
                    if any(kw in description for kw in tools_keywords):
                        tools_count = 1  # Assume at least 1 tool

                # Extract repository URL
                repository_url = self._extract_repo_url(pkg_data.get("repository"))

                # Create metadata object
                metadata = MCPServerMetadata(
                    name=package_name,
                    display_name=pkg_data.get("name"),
                    description=pkg_data.get("description", ""),
                    source_type="npm",
                    source_url=f"https://www.npmjs.com/package/{package_name}",
                    npm_package_name=package_name,
                    latest_version=latest_version,
                    available_versions=list(pkg_data.get("versions", {}).keys()),
                    runtime_type="nodejs",
                    runtime_version=version_data.get("engines", {}).get("node"),
                    protocol_version=mcp_config.get("protocolVersion"),
                    tools_count=tools_count,
                    resources_count=len(mcp_config.get("resources", [])),
                    prompts_count=len(mcp_config.get("prompts", [])),
                    manifest=version_data,
                    readme=pkg_data.get("readme"),
                    requires_oauth=mcp_config.get("requiresOAuth", False),
                    oauth_providers=mcp_config.get("oauthProviders", []),
                    download_count=self._get_download_count(pkg_data),
                    author=self._extract_author(pkg_data.get("author")),
                    license=pkg_data.get("license"),
                    homepage_url=pkg_data.get("homepage"),
                    repository_url=repository_url,
                )

                logger.debug(f"Successfully parsed metadata for {package_name}")
                return metadata

            except httpx.HTTPError as e:
                logger.error(f"Failed to fetch NPM package {package_name}: {e}")
                return None
            except Exception as e:
                logger.error(f"Error parsing NPM package {package_name}: {e}")
                return None

    def _extract_repo_url(self, repo) -> Optional[str]:
        """Extract repository URL from package.json repository field.

        Args:
            repo: Repository field from package.json

        Returns:
            Clean repository URL or None
        """
        if not repo:
            return None

        if isinstance(repo, str):
            # Clean up git+https://... format
            url = repo.replace("git+", "").replace(".git", "")
            return url

        if isinstance(repo, dict):
            url = repo.get("url", "")
            url = url.replace("git+", "").replace(".git", "")
            return url

        return None

    def _extract_author(self, author) -> Optional[str]:
        """Extract author name from package.json author field.

        Args:
            author: Author field (string or dict)

        Returns:
            Author name or None
        """
        if not author:
            return None

        if isinstance(author, str):
            return author

        if isinstance(author, dict):
            return author.get("name")

        return None

    def _get_download_count(self, pkg_data: dict) -> int:
        """Get download count from package data.

        Note: NPM registry doesn't include download counts in package metadata.
        We'd need to query a separate API (npm-stat or similar) for this.
        For now, return 0.

        Args:
            pkg_data: Package data from NPM

        Returns:
            Download count (0 for now)
        """
        # TODO: Query npm-stat API or similar service
        return 0

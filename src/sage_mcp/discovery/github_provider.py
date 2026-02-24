"""GitHub repository discovery provider for MCP servers."""

import httpx
import base64
import json
import logging
import os
from typing import List, Optional

from .base import BaseDiscoveryProvider, MCPServerMetadata

logger = logging.getLogger(__name__)


class GitHubDiscoveryProvider(BaseDiscoveryProvider):
    """Discover MCP servers from GitHub repositories."""

    def __init__(self):
        """Initialize GitHub discovery provider."""
        self.api_url = "https://api.github.com"
        self.token = os.getenv("GITHUB_DISCOVERY_TOKEN")  # Optional: higher rate limits
        self.timeout = 30.0

    def _get_headers(self) -> dict:
        """Get HTTP headers for GitHub API requests.

        Returns:
            Headers dict with authentication if token is available
        """
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "SageMCP-Discovery/1.0"
        }

        if self.token:
            headers["Authorization"] = f"token {self.token}"

        return headers

    async def search(self, query: str = "", limit: int = 20) -> List[MCPServerMetadata]:
        """Search GitHub for repositories with MCP server topics.

        Args:
            query: Additional search terms
            limit: Maximum results

        Returns:
            List of discovered MCP servers
        """
        servers = []
        headers = self._get_headers()

        async with httpx.AsyncClient() as client:
            try:
                # Build search query - search for repos with MCP topics
                search_terms = ["topic:mcp", "topic:model-context-protocol"]
                if query:
                    search_terms.append(query)

                search_query = " ".join(search_terms)

                params = {
                    "q": search_query,
                    "sort": "stars",
                    "order": "desc",
                    "per_page": limit
                }

                logger.info(f"Searching GitHub with query: {search_query}")
                response = await client.get(
                    f"{self.api_url}/search/repositories",
                    headers=headers,
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()

                logger.info(f"Found {len(data.get('items', []))} GitHub repositories")

                for repo in data.get("items", []):
                    metadata = await self.get_details(repo["full_name"])
                    if metadata:
                        servers.append(metadata)

            except httpx.HTTPError as e:
                logger.error(f"GitHub search failed: {e}")
            except Exception as e:
                logger.error(f"Error during GitHub search: {e}")

        return servers

    async def get_details(self, repo_full_name: str) -> Optional[MCPServerMetadata]:
        """Get detailed repository information.

        Args:
            repo_full_name: Repository full name (owner/repo)

        Returns:
            MCPServerMetadata or None if fetch fails
        """
        headers = self._get_headers()

        async with httpx.AsyncClient() as client:
            try:
                logger.debug(f"Fetching GitHub repo details: {repo_full_name}")

                # Get repo metadata
                response = await client.get(
                    f"{self.api_url}/repos/{repo_full_name}",
                    headers=headers,
                    timeout=self.timeout
                )
                response.raise_for_status()
                repo_data = response.json()

                # Try to fetch manifest files
                manifest = await self._fetch_manifest(client, repo_full_name, headers)
                readme = await self._fetch_readme(client, repo_full_name, headers)

                # Detect runtime type
                runtime_type = await self._detect_runtime(client, repo_full_name, headers)

                # Detect OAuth requirement
                requires_oauth = self._detect_oauth_requirement(manifest, readme)

                # Extract tools count from manifest
                tools_count = 0
                if manifest:
                    # Check for MCP tools definition
                    if "mcp" in manifest and "tools" in manifest["mcp"]:
                        tools_count = len(manifest["mcp"]["tools"])
                    elif "tools" in manifest:
                        tools_count = len(manifest["tools"])

                # Get latest release version
                latest_version = await self._get_latest_release(client, repo_full_name, headers)

                metadata = MCPServerMetadata(
                    name=repo_data["name"],
                    display_name=repo_data["full_name"],
                    description=repo_data.get("description", ""),
                    source_type="github",
                    source_url=repo_data["html_url"],
                    github_repo=repo_full_name,
                    latest_version=latest_version,
                    runtime_type=runtime_type,
                    manifest=manifest,
                    readme=readme,
                    requires_oauth=requires_oauth,
                    tools_count=tools_count,
                    star_count=repo_data.get("stargazers_count", 0),
                    author=repo_data.get("owner", {}).get("login"),
                    license=repo_data.get("license", {}).get("spdx_id") if repo_data.get("license") else None,
                    repository_url=repo_data["html_url"],
                    homepage_url=repo_data.get("homepage"),
                )

                logger.debug(f"Successfully parsed metadata for {repo_full_name}")
                return metadata

            except httpx.HTTPError as e:
                logger.error(f"Failed to fetch GitHub repo {repo_full_name}: {e}")
                return None
            except Exception as e:
                logger.error(f"Error parsing GitHub repo {repo_full_name}: {e}")
                return None

    async def _fetch_manifest(
        self,
        client: httpx.AsyncClient,
        repo: str,
        headers: dict
    ) -> Optional[dict]:
        """Fetch package.json, mcp.json, or pyproject.toml from repository.

        Args:
            client: HTTP client
            repo: Repository full name
            headers: Request headers

        Returns:
            Parsed manifest dict or None
        """
        # Try multiple manifest file names
        manifest_files = ["package.json", "mcp.json", "pyproject.toml"]

        for filename in manifest_files:
            try:
                response = await client.get(
                    f"{self.api_url}/repos/{repo}/contents/{filename}",
                    headers=headers,
                    timeout=10
                )

                if response.status_code == 200:
                    content_data = response.json()

                    # Decode base64 content
                    decoded = base64.b64decode(content_data["content"]).decode("utf-8")

                    # Parse JSON files
                    if filename.endswith(".json"):
                        return json.loads(decoded)

                    # For TOML, we'd need a TOML parser (skip for now)
                    # TODO: Add toml parsing for Python projects

            except Exception as e:
                logger.debug(f"Could not fetch {filename} from {repo}: {e}")
                continue

        return None

    async def _fetch_readme(
        self,
        client: httpx.AsyncClient,
        repo: str,
        headers: dict
    ) -> Optional[str]:
        """Fetch README.md from repository.

        Args:
            client: HTTP client
            repo: Repository full name
            headers: Request headers

        Returns:
            README content or None
        """
        try:
            # GitHub provides a special endpoint for README
            response = await client.get(
                f"{self.api_url}/repos/{repo}/readme",
                headers={**headers, "Accept": "application/vnd.github.v3.raw"},
                timeout=10
            )

            if response.status_code == 200:
                return response.text

        except Exception as e:
            logger.debug(f"Could not fetch README from {repo}: {e}")

        return None

    async def _detect_runtime(
        self,
        client: httpx.AsyncClient,
        repo: str,
        headers: dict
    ) -> str:
        """Detect runtime type from repository files.

        Args:
            client: HTTP client
            repo: Repository full name
            headers: Request headers

        Returns:
            Runtime type string (nodejs, python, go, rust, binary)
        """
        # Check for package.json (Node.js)
        try:
            response = await client.get(
                f"{self.api_url}/repos/{repo}/contents/package.json",
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                return "nodejs"
        except Exception:
            pass

        # Check for Python files
        python_files = ["pyproject.toml", "requirements.txt", "setup.py", "Pipfile"]
        for filename in python_files:
            try:
                response = await client.get(
                    f"{self.api_url}/repos/{repo}/contents/{filename}",
                    headers=headers,
                    timeout=10
                )
                if response.status_code == 200:
                    return "python"
            except Exception:
                continue

        # Check for go.mod (Go)
        try:
            response = await client.get(
                f"{self.api_url}/repos/{repo}/contents/go.mod",
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                return "go"
        except Exception:
            pass

        # Check for Cargo.toml (Rust)
        try:
            response = await client.get(
                f"{self.api_url}/repos/{repo}/contents/Cargo.toml",
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                return "rust"
        except Exception:
            pass

        return "binary"  # Unknown runtime

    async def _get_latest_release(
        self,
        client: httpx.AsyncClient,
        repo: str,
        headers: dict
    ) -> Optional[str]:
        """Get latest release tag.

        Args:
            client: HTTP client
            repo: Repository full name
            headers: Request headers

        Returns:
            Latest release tag or None
        """
        try:
            response = await client.get(
                f"{self.api_url}/repos/{repo}/releases/latest",
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get("tag_name")
        except Exception:
            pass

        return None

    def _detect_oauth_requirement(
        self,
        manifest: Optional[dict],
        readme: Optional[str]
    ) -> bool:
        """Detect if OAuth is required from manifest or README.

        Args:
            manifest: Parsed manifest file
            readme: README content

        Returns:
            True if OAuth is likely required
        """
        # Check manifest for OAuth indicators
        if manifest:
            # Check MCP-specific OAuth field
            if manifest.get("mcp", {}).get("requiresOAuth"):
                return True

            # Check for OAuth-related dependencies
            deps = {
                **manifest.get("dependencies", {}),
                **manifest.get("devDependencies", {})
            }

            oauth_packages = [
                "@modelcontextprotocol/sdk-oauth",
                "passport",
                "oauth2",
                "google-auth-library",
                "octokit",  # GitHub API
            ]

            if any(pkg in deps for pkg in oauth_packages):
                return True

        # Check README for OAuth mentions
        if readme:
            oauth_keywords = [
                "OAuth",
                "authentication",
                "access token",
                "GITHUB_TOKEN",
                "API key",
                "credentials"
            ]
            readme_lower = readme.lower()
            if sum(1 for kw in oauth_keywords if kw.lower() in readme_lower) >= 2:
                return True

        return False

"""Base connector interface for plugin system."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol

from mcp import types

from ..models.connector import Connector
from ..models.oauth_credential import OAuthCredential
from .exceptions import ConnectorAuthError

logger = logging.getLogger(__name__)


class ConnectorPlugin(Protocol):
    """Protocol for connector plugins."""

    @property
    def name(self) -> str:
        """Connector name."""
        ...

    @property
    def display_name(self) -> str:
        """Human-readable display name."""
        ...

    @property
    def description(self) -> str:
        """Connector description."""
        ...

    @property
    def requires_oauth(self) -> bool:
        """Whether this connector requires OAuth authentication."""
        ...

    async def get_tools(self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None) -> List[types.Tool]:
        """Get available tools for this connector."""
        ...

    async def get_resources(self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None) -> List[types.Resource]:
        """Get available resources for this connector."""
        ...

    async def execute_tool(
        self,
        connector: Connector,
        tool_name: str,
        arguments: Dict[str, Any],
        oauth_cred: Optional[OAuthCredential] = None
    ) -> str:
        """Execute a tool action."""
        ...

    async def read_resource(
        self,
        connector: Connector,
        resource_path: str,
        oauth_cred: Optional[OAuthCredential] = None
    ) -> str:
        """Read a resource."""
        ...


class BaseConnector(ABC):
    """Base class for all connectors."""

    def __init__(self):
        self._name = self.__class__.__name__.lower().replace("connector", "")

    @property
    def name(self) -> str:
        """Connector name."""
        return self._name

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable display name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Connector description."""
        pass

    @property
    @abstractmethod
    def requires_oauth(self) -> bool:
        """Whether this connector requires OAuth authentication."""
        pass

    @abstractmethod
    async def get_tools(self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None) -> List[types.Tool]:
        """Get available tools for this connector."""
        pass

    @abstractmethod
    async def get_resources(self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None) -> List[types.Resource]:
        """Get available resources for this connector."""
        pass

    @abstractmethod
    async def execute_tool(
        self,
        connector: Connector,
        tool_name: str,
        arguments: Dict[str, Any],
        oauth_cred: Optional[OAuthCredential] = None
    ) -> str:
        """Execute a tool action."""
        pass

    @abstractmethod
    async def read_resource(
        self,
        connector: Connector,
        resource_path: str,
        oauth_cred: Optional[OAuthCredential] = None
    ) -> str:
        """Read a resource."""
        pass

    def validate_oauth_credential(self, oauth_cred: OAuthCredential) -> bool:
        """Validate OAuth credentials for this connector."""
        if not self.requires_oauth:
            return True

        if not oauth_cred:
            logger.debug("OAuth credential is None")
            return False

        if not oauth_cred.is_active:
            logger.debug("OAuth credential is not active: is_active=%s", oauth_cred.is_active)
            return False

        # Check if token is expired
        if oauth_cred.is_expired:
            logger.debug("OAuth credential is expired: expires_at=%s", oauth_cred.expires_at)
            return False

        logger.debug("OAuth credential validation passed")
        return True

    async def _make_authenticated_request(
        self,
        method: str,
        url: str,
        oauth_cred: OAuthCredential,
        **kwargs
    ) -> Any:
        """Make an authenticated HTTP request using OAuth credentials.

        Uses a shared HTTP client with connection pooling for better performance.
        Automatically retries on transient failures (429, 5xx, connection errors).
        """
        from .http_client import get_http_client
        from .retry import retry_with_backoff

        if not self.validate_oauth_credential(oauth_cred):
            raise ConnectorAuthError("Invalid or expired OAuth credentials")

        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {oauth_cred.access_token}"
        kwargs["headers"] = headers

        async def _do_request():
            client = get_http_client()
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return response

        return await retry_with_backoff(_do_request)


class ApiKeyBaseConnector(BaseConnector):
    """Base class for connectors that use API keys instead of OAuth.

    API key is stored in connector.configuration["api_key"].
    Used by AI coding tool connectors (Copilot, Claude Code, Codex, Cursor, Windsurf).
    """

    @property
    def requires_oauth(self) -> bool:
        return False

    def _get_api_key(self, connector: Connector) -> str:
        """Extract API key from connector configuration."""
        return (connector.configuration or {}).get("api_key", "")

    async def _make_api_key_request(
        self,
        method: str,
        url: str,
        connector: Connector,
        auth_header: str = "Authorization",
        auth_prefix: str = "Bearer",
        **kwargs,
    ) -> Any:
        """Make an authenticated HTTP request using an API key.

        Args:
            method: HTTP method.
            url: Request URL.
            connector: Connector instance with configuration containing api_key.
            auth_header: Header name for the API key (default: "Authorization").
            auth_prefix: Prefix before the key value (default: "Bearer").
                         Use "" for headers like x-api-key that need no prefix.
            **kwargs: Additional arguments passed to httpx.request().

        Returns:
            httpx.Response with status already checked.
        """
        from .http_client import get_http_client
        from .retry import retry_with_backoff

        api_key = self._get_api_key(connector)
        if not api_key:
            raise ConnectorAuthError("API key not configured")

        headers = kwargs.get("headers", {})
        if auth_prefix:
            headers[auth_header] = f"{auth_prefix} {api_key}"
        else:
            headers[auth_header] = api_key
        kwargs["headers"] = headers

        async def _do_request():
            client = get_http_client()
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return response

        return await retry_with_backoff(_do_request)

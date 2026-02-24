"""Connector-specific exception types.

These exceptions are used internally by connectors in _make_authenticated_request()
and caught in each connector's try/except. The MCP server layer already catches
Exception generically, so these don't break the existing interface.
"""

from typing import Optional


class ConnectorError(Exception):
    """Base exception for all connector errors."""

    def __init__(self, message: str, connector_name: str = ""):
        self.connector_name = connector_name
        super().__init__(message)


class ConnectorAuthError(ConnectorError):
    """Authentication or authorization failure (401/403, expired token)."""

    pass


class ConnectorRateLimitError(ConnectorError):
    """Rate limit exceeded (429). Includes retry_after hint if available."""

    def __init__(
        self,
        message: str,
        retry_after: Optional[float] = None,
        connector_name: str = "",
    ):
        self.retry_after = retry_after
        super().__init__(message, connector_name)


class ConnectorAPIError(ConnectorError):
    """API returned an error response (4xx/5xx)."""

    def __init__(
        self,
        message: str,
        status_code: int = 0,
        response_body: str = "",
        connector_name: str = "",
    ):
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(message, connector_name)


class ConnectorNotFoundError(ConnectorAPIError):
    """Resource not found (404)."""

    def __init__(self, message: str, connector_name: str = ""):
        super().__init__(message, status_code=404, connector_name=connector_name)


class ConnectorValidationError(ConnectorError):
    """Invalid input provided to a connector tool."""

    pass


class ConnectorTimeoutError(ConnectorError):
    """Request timed out."""

    pass

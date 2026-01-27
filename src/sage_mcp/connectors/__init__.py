"""Connector plugin system for Sage MCP."""

from .base import BaseConnector, ConnectorPlugin
from .registry import ConnectorRegistry

# Import all connector implementations to trigger registration
from . import github  # noqa: F401
from . import google_docs  # noqa: F401
from . import google_calendar  # noqa: F401
from . import jira  # noqa: F401
from . import notion  # noqa: F401
from . import slack  # noqa: F401
from . import zoom  # noqa: F401
# TODO: Add other connectors as they are implemented
# from . import gitlab
# from . import discord
# from . import custom

__all__ = ["BaseConnector", "ConnectorPlugin", "ConnectorRegistry"]

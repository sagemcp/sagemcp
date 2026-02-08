"""Connector plugin system for Sage MCP."""

from .base import BaseConnector, ConnectorPlugin
from .registry import ConnectorRegistry

# Import all connector implementations to trigger registration
from . import github  # noqa: F401
from . import google_docs  # noqa: F401
from . import google_sheets  # noqa: F401
from . import gmail  # noqa: F401
from . import google_slides  # noqa: F401
from . import jira  # noqa: F401
from . import notion  # noqa: F401
from . import slack  # noqa: F401
from . import teams  # noqa: F401
from . import zoom  # noqa: F401
from . import outlook  # noqa: F401
from . import excel  # noqa: F401
from . import powerpoint  # noqa: F401
from . import confluence  # noqa: F401
from . import bitbucket  # noqa: F401
from . import gitlab  # noqa: F401
from . import linear  # noqa: F401
from . import discord  # noqa: F401

# AI coding tool intelligence connectors
from . import copilot  # noqa: F401
from . import claude_code  # noqa: F401
from . import codex  # noqa: F401
from . import cursor  # noqa: F401
from . import windsurf  # noqa: F401
# TODO: Add other connectors as they are implemented
# from . import custom

__all__ = ["BaseConnector", "ConnectorPlugin", "ConnectorRegistry"]

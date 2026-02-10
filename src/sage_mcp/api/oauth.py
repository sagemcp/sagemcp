"""OAuth API routes for connector authentication."""

import os
import secrets
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, field_validator
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_db_session
from ..models.oauth_credential import OAuthCredential
from ..models.oauth_config import OAuthConfig
from ..models.tenant import Tenant

router = APIRouter()

# OAuth provider configurations
# Only include providers that have implemented connectors
OAUTH_PROVIDERS = {
    "github": {
        "name": "GitHub",
        "auth_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "user_url": "https://api.github.com/user",
        "scopes": ["repo", "user:email", "read:org", "manage_billing:copilot"],
        "client_id": (
            os.getenv("GITHUB_CLIENT_ID")
            if os.getenv("GITHUB_CLIENT_ID")
            and os.getenv("GITHUB_CLIENT_ID") != "your-github-client-id"
            else None
        ),
        "client_secret": (
            os.getenv("GITHUB_CLIENT_SECRET")
            if os.getenv("GITHUB_CLIENT_SECRET")
            and os.getenv("GITHUB_CLIENT_SECRET") != "your-github-client-secret"
            else None
        ),
    },
    "slack": {
        "name": "Slack",
        "auth_url": "https://slack.com/oauth/v2/authorize",
        "token_url": "https://slack.com/api/oauth.v2.access",
        "user_url": "https://slack.com/api/auth.test",
        "scopes": [
            "channels:history",
            "channels:read",
            "chat:write",
            "users:read",
            "team:read",
            "reactions:read",
            "reactions:write"
        ],
        "client_id": (
            os.getenv("SLACK_CLIENT_ID")
            if os.getenv("SLACK_CLIENT_ID")
            and os.getenv("SLACK_CLIENT_ID") != "your-slack-client-id"
            else None
        ),
        "client_secret": (
            os.getenv("SLACK_CLIENT_SECRET")
            if os.getenv("SLACK_CLIENT_SECRET")
            and os.getenv("SLACK_CLIENT_SECRET") != "your-slack-client-secret"
            else None
        ),
    },
    "google_docs": {
        "name": "Google Docs",
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "user_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "scopes": [
            "https://www.googleapis.com/auth/documents",
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile"
        ],
        "client_id": (
            os.getenv("GOOGLE_CLIENT_ID")
            if os.getenv("GOOGLE_CLIENT_ID")
            and os.getenv("GOOGLE_CLIENT_ID") != "your-google-client-id"
            else None
        ),
        "client_secret": (
            os.getenv("GOOGLE_CLIENT_SECRET")
            if os.getenv("GOOGLE_CLIENT_SECRET")
            and os.getenv("GOOGLE_CLIENT_SECRET") != "your-google-client-secret"
            else None
        ),
    },
    "jira": {
        "name": "Jira",
        "auth_url": "https://auth.atlassian.com/authorize",
        "token_url": "https://auth.atlassian.com/oauth/token",
        "user_url": "https://api.atlassian.com/me",
        "scopes": [
            "read:jira-work",
            "write:jira-work",
            "read:jira-user",
            "offline_access"
        ],
        "client_id": (
            os.getenv("JIRA_CLIENT_ID")
            if os.getenv("JIRA_CLIENT_ID")
            and os.getenv("JIRA_CLIENT_ID") != "your-jira-client-id"
            else None
        ),
        "client_secret": (
            os.getenv("JIRA_CLIENT_SECRET")
            if os.getenv("JIRA_CLIENT_SECRET")
            and os.getenv("JIRA_CLIENT_SECRET") != "your-jira-client-secret"
            else None
        ),
    },
    "notion": {
        "name": "Notion",
        "auth_url": "https://api.notion.com/v1/oauth/authorize",
        "token_url": "https://api.notion.com/v1/oauth/token",
        "user_url": "https://api.notion.com/v1/users/me",
        "scopes": [],  # Notion doesn't use scopes in the same way
        "client_id": (
            os.getenv("NOTION_CLIENT_ID")
            if os.getenv("NOTION_CLIENT_ID")
            and os.getenv("NOTION_CLIENT_ID") != "your-notion-client-id"
            else None
        ),
        "client_secret": (
            os.getenv("NOTION_CLIENT_SECRET")
            if os.getenv("NOTION_CLIENT_SECRET")
            and os.getenv("NOTION_CLIENT_SECRET") != "your-notion-client-secret"
            else None
        ),
    },
    "zoom": {
        "name": "Zoom",
        "auth_url": "https://zoom.us/oauth/authorize",
        "token_url": "https://zoom.us/oauth/token",
        "user_url": "https://api.zoom.us/v2/users/me",
        "scopes": [
            "meeting:read",
            "meeting:write",
            "recording:read",
            "user:read"
        ],
        "client_id": (
            os.getenv("ZOOM_CLIENT_ID")
            if os.getenv("ZOOM_CLIENT_ID")
            and os.getenv("ZOOM_CLIENT_ID") != "your-zoom-client-id"
            else None
        ),
        "client_secret": (
            os.getenv("ZOOM_CLIENT_SECRET")
            if os.getenv("ZOOM_CLIENT_SECRET")
            and os.getenv("ZOOM_CLIENT_SECRET") != "your-zoom-client-secret"
            else None
        ),
    },
    "google_sheets": {
        "name": "Google Sheets",
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "user_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "scopes": [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile"
        ],
        "client_id": (
            os.getenv("GOOGLE_CLIENT_ID")
            if os.getenv("GOOGLE_CLIENT_ID")
            and os.getenv("GOOGLE_CLIENT_ID") != "your-google-client-id"
            else None
        ),
        "client_secret": (
            os.getenv("GOOGLE_CLIENT_SECRET")
            if os.getenv("GOOGLE_CLIENT_SECRET")
            and os.getenv("GOOGLE_CLIENT_SECRET") != "your-google-client-secret"
            else None
        ),
    },
    "gmail": {
        "name": "Gmail",
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "user_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "scopes": [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/gmail.labels",
            "https://www.googleapis.com/auth/userinfo.email"
        ],
        "client_id": (
            os.getenv("GOOGLE_CLIENT_ID")
            if os.getenv("GOOGLE_CLIENT_ID")
            and os.getenv("GOOGLE_CLIENT_ID") != "your-google-client-id"
            else None
        ),
        "client_secret": (
            os.getenv("GOOGLE_CLIENT_SECRET")
            if os.getenv("GOOGLE_CLIENT_SECRET")
            and os.getenv("GOOGLE_CLIENT_SECRET") != "your-google-client-secret"
            else None
        ),
    },
    "google_slides": {
        "name": "Google Slides",
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "user_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "scopes": [
            "https://www.googleapis.com/auth/presentations",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/userinfo.email"
        ],
        "client_id": (
            os.getenv("GOOGLE_CLIENT_ID")
            if os.getenv("GOOGLE_CLIENT_ID")
            and os.getenv("GOOGLE_CLIENT_ID") != "your-google-client-id"
            else None
        ),
        "client_secret": (
            os.getenv("GOOGLE_CLIENT_SECRET")
            if os.getenv("GOOGLE_CLIENT_SECRET")
            and os.getenv("GOOGLE_CLIENT_SECRET") != "your-google-client-secret"
            else None
        ),
    },
    "confluence": {
        "name": "Confluence",
        "auth_url": "https://auth.atlassian.com/authorize",
        "token_url": "https://auth.atlassian.com/oauth/token",
        "user_url": "https://api.atlassian.com/me",
        "scopes": [
            "read:confluence-content.all",
            "write:confluence-content",
            "read:confluence-space.summary",
            "search:confluence",
            "offline_access"
        ],
        "client_id": (
            os.getenv("JIRA_CLIENT_ID")
            if os.getenv("JIRA_CLIENT_ID")
            and os.getenv("JIRA_CLIENT_ID") != "your-jira-client-id"
            else None
        ),
        "client_secret": (
            os.getenv("JIRA_CLIENT_SECRET")
            if os.getenv("JIRA_CLIENT_SECRET")
            and os.getenv("JIRA_CLIENT_SECRET") != "your-jira-client-secret"
            else None
        ),
    },
    "gitlab": {
        "name": "GitLab",
        "auth_url": "https://gitlab.com/oauth/authorize",
        "token_url": "https://gitlab.com/oauth/token",
        "user_url": "https://gitlab.com/api/v4/user",
        "scopes": [
            "api",
            "read_user",
            "read_repository"
        ],
        "client_id": (
            os.getenv("GITLAB_CLIENT_ID")
            if os.getenv("GITLAB_CLIENT_ID")
            and os.getenv("GITLAB_CLIENT_ID") != "your-gitlab-client-id"
            else None
        ),
        "client_secret": (
            os.getenv("GITLAB_CLIENT_SECRET")
            if os.getenv("GITLAB_CLIENT_SECRET")
            and os.getenv("GITLAB_CLIENT_SECRET") != "your-gitlab-client-secret"
            else None
        ),
    },
    "bitbucket": {
        "name": "Bitbucket",
        "auth_url": "https://bitbucket.org/site/oauth2/authorize",
        "token_url": "https://bitbucket.org/site/oauth2/access_token",
        "user_url": "https://api.bitbucket.org/2.0/user",
        "scopes": [
            "repository",
            "pullrequest",
            "issue",
            "pipeline",
            "account"
        ],
        "client_id": (
            os.getenv("BITBUCKET_CLIENT_ID")
            if os.getenv("BITBUCKET_CLIENT_ID")
            and os.getenv("BITBUCKET_CLIENT_ID") != "your-bitbucket-client-id"
            else None
        ),
        "client_secret": (
            os.getenv("BITBUCKET_CLIENT_SECRET")
            if os.getenv("BITBUCKET_CLIENT_SECRET")
            and os.getenv("BITBUCKET_CLIENT_SECRET") != "your-bitbucket-client-secret"
            else None
        ),
    },
    "linear": {
        "name": "Linear",
        "auth_url": "https://linear.app/oauth/authorize",
        "token_url": "https://api.linear.app/oauth/token",
        "user_url": "https://api.linear.app/graphql",
        "scopes": [
            "read",
            "write",
            "issues:create",
            "comments:create"
        ],
        "client_id": (
            os.getenv("LINEAR_CLIENT_ID")
            if os.getenv("LINEAR_CLIENT_ID")
            and os.getenv("LINEAR_CLIENT_ID") != "your-linear-client-id"
            else None
        ),
        "client_secret": (
            os.getenv("LINEAR_CLIENT_SECRET")
            if os.getenv("LINEAR_CLIENT_SECRET")
            and os.getenv("LINEAR_CLIENT_SECRET") != "your-linear-client-secret"
            else None
        ),
    },
    "discord": {
        "name": "Discord",
        "auth_url": "https://discord.com/api/oauth2/authorize",
        "token_url": "https://discord.com/api/oauth2/token",
        "user_url": "https://discord.com/api/v10/users/@me",
        "scopes": [
            "identify",
            "guilds",
            "guilds.members.read",
            "bot"
        ],
        "client_id": (
            os.getenv("DISCORD_CLIENT_ID")
            if os.getenv("DISCORD_CLIENT_ID")
            and os.getenv("DISCORD_CLIENT_ID") != "your-discord-client-id"
            else None
        ),
        "client_secret": (
            os.getenv("DISCORD_CLIENT_SECRET")
            if os.getenv("DISCORD_CLIENT_SECRET")
            and os.getenv("DISCORD_CLIENT_SECRET") != "your-discord-client-secret"
            else None
        ),
    },
    "microsoft": {
        "name": "Microsoft 365",
        "auth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "user_url": "https://graph.microsoft.com/v1.0/me",
        "scopes": [
            "openid",
            "profile",
            "email",
            "offline_access",
            "Mail.ReadWrite",
            "Mail.Send",
            "ChannelMessage.Send",
            "Team.ReadBasic.All",
            "Channel.ReadBasic.All",
            "Chat.ReadWrite",
            "Files.ReadWrite.All",
            "User.Read"
        ],
        "client_id": (
            os.getenv("MICROSOFT_CLIENT_ID")
            if os.getenv("MICROSOFT_CLIENT_ID")
            and os.getenv("MICROSOFT_CLIENT_ID") != "your-microsoft-client-id"
            else None
        ),
        "client_secret": (
            os.getenv("MICROSOFT_CLIENT_SECRET")
            if os.getenv("MICROSOFT_CLIENT_SECRET")
            and os.getenv("MICROSOFT_CLIENT_SECRET") != "your-microsoft-client-secret"
            else None
        ),
    },
    "google_calendar": {
        "name": "Google Calendar",
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "user_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "scopes": [
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/calendar.events",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile"
        ],
        "client_id": (
            os.getenv("GOOGLE_CLIENT_ID")
            if os.getenv("GOOGLE_CLIENT_ID")
            and os.getenv("GOOGLE_CLIENT_ID") != "your-google-client-id"
            else None
        ),
        "client_secret": (
            os.getenv("GOOGLE_CLIENT_SECRET")
            if os.getenv("GOOGLE_CLIENT_SECRET")
            and os.getenv("GOOGLE_CLIENT_SECRET") != "your-google-client-secret"
            else None
        ),
    },
    "teams": {
        "name": "Microsoft Teams",
        "auth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "user_url": "https://graph.microsoft.com/v1.0/me",
        "scopes": [
            "openid",
            "profile",
            "email",
            "offline_access",
            "ChannelMessage.Send",
            "Team.ReadBasic.All",
            "Channel.ReadBasic.All",
            "Chat.ReadWrite",
            "User.Read"
        ],
        "client_id": (
            os.getenv("MICROSOFT_CLIENT_ID")
            if os.getenv("MICROSOFT_CLIENT_ID")
            and os.getenv("MICROSOFT_CLIENT_ID") != "your-microsoft-client-id"
            else None
        ),
        "client_secret": (
            os.getenv("MICROSOFT_CLIENT_SECRET")
            if os.getenv("MICROSOFT_CLIENT_SECRET")
            and os.getenv("MICROSOFT_CLIENT_SECRET") != "your-microsoft-client-secret"
            else None
        ),
    },
    "outlook": {
        "name": "Outlook",
        "auth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "user_url": "https://graph.microsoft.com/v1.0/me",
        "scopes": [
            "openid",
            "profile",
            "email",
            "offline_access",
            "Mail.ReadWrite",
            "Mail.Send",
            "User.Read"
        ],
        "client_id": (
            os.getenv("MICROSOFT_CLIENT_ID")
            if os.getenv("MICROSOFT_CLIENT_ID")
            and os.getenv("MICROSOFT_CLIENT_ID") != "your-microsoft-client-id"
            else None
        ),
        "client_secret": (
            os.getenv("MICROSOFT_CLIENT_SECRET")
            if os.getenv("MICROSOFT_CLIENT_SECRET")
            and os.getenv("MICROSOFT_CLIENT_SECRET") != "your-microsoft-client-secret"
            else None
        ),
    },
    "excel": {
        "name": "Excel",
        "auth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "user_url": "https://graph.microsoft.com/v1.0/me",
        "scopes": [
            "openid",
            "profile",
            "email",
            "offline_access",
            "Files.ReadWrite.All",
            "User.Read"
        ],
        "client_id": (
            os.getenv("MICROSOFT_CLIENT_ID")
            if os.getenv("MICROSOFT_CLIENT_ID")
            and os.getenv("MICROSOFT_CLIENT_ID") != "your-microsoft-client-id"
            else None
        ),
        "client_secret": (
            os.getenv("MICROSOFT_CLIENT_SECRET")
            if os.getenv("MICROSOFT_CLIENT_SECRET")
            and os.getenv("MICROSOFT_CLIENT_SECRET") != "your-microsoft-client-secret"
            else None
        ),
    },
    "powerpoint": {
        "name": "PowerPoint",
        "auth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "user_url": "https://graph.microsoft.com/v1.0/me",
        "scopes": [
            "openid",
            "profile",
            "email",
            "offline_access",
            "Files.ReadWrite.All",
            "User.Read"
        ],
        "client_id": (
            os.getenv("MICROSOFT_CLIENT_ID")
            if os.getenv("MICROSOFT_CLIENT_ID")
            and os.getenv("MICROSOFT_CLIENT_ID") != "your-microsoft-client-id"
            else None
        ),
        "client_secret": (
            os.getenv("MICROSOFT_CLIENT_SECRET")
            if os.getenv("MICROSOFT_CLIENT_SECRET")
            and os.getenv("MICROSOFT_CLIENT_SECRET") != "your-microsoft-client-secret"
            else None
        ),
    },
}


class OAuthCredentialResponse(BaseModel):
    id: str
    provider: str
    provider_user_id: str
    provider_username: Optional[str]
    token_type: str
    scopes: Optional[str]
    is_active: bool
    expires_at: Optional[datetime]
    created_at: datetime

    @field_validator('id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True


class OAuthConfigCreate(BaseModel):
    """Request model for creating OAuth configuration."""
    provider: str
    client_id: str
    client_secret: str


class OAuthConfigResponse(BaseModel):
    """Response model for OAuth configuration."""
    id: str
    provider: str
    client_id: str
    is_active: bool
    created_at: datetime

    @field_validator('id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True


@router.get("/{tenant_slug}/auth/{provider}")
async def initiate_oauth(
    tenant_slug: str,
    provider: str,
    request: Request,
    custom_redirect_uri: Optional[str] = None,
    custom_state: Optional[str] = None,
    session: AsyncSession = Depends(get_db_session)
):
    """Initiate OAuth flow for a provider.

    Args:
        tenant_slug: Tenant identifier
        provider: OAuth provider (github, slack, etc.)
        custom_redirect_uri: Optional custom redirect URI for CLI flows
        custom_state: Optional custom state parameter for CSRF protection
        request: FastAPI request object
        session: Database session
    """
    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported provider: {provider}"
        )

    # Verify tenant exists
    tenant_result = await session.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    provider_config = OAUTH_PROVIDERS[provider]

    # Check for tenant-specific OAuth configuration first
    tenant_config_result = await session.execute(
        select(OAuthConfig).where(
            OAuthConfig.tenant_id == tenant.id,
            OAuthConfig.provider == provider,
            OAuthConfig.is_active.is_(True)
        )
    )
    tenant_oauth_config = tenant_config_result.scalar_one_or_none()

    # Use tenant config if available, otherwise fall back to global config
    if tenant_oauth_config:
        client_id = tenant_oauth_config.client_id
        client_secret = tenant_oauth_config.client_secret
    else:
        client_id = provider_config["client_id"]
        client_secret = provider_config["client_secret"]

    if not client_id or not client_secret:
        raise HTTPException(
            status_code=500,
            detail=(
                f"OAuth not configured for {provider}. "
                "Please configure OAuth credentials for this tenant."
            )
        )

    # Generate state parameter for CSRF protection
    # Use custom state if provided (for CLI flows), otherwise generate new one
    state = custom_state if custom_state else secrets.token_urlsafe(32)

    # Build redirect URI
    # Use custom redirect URI if provided (for CLI flows)
    if custom_redirect_uri:
        # Validate that custom redirect URI is localhost (security check)
        if not (custom_redirect_uri.startswith('http://localhost:') or
                custom_redirect_uri.startswith('http://127.0.0.1:')):
            raise HTTPException(
                status_code=400,
                detail="Custom redirect URI must be localhost"
            )
        redirect_uri = custom_redirect_uri
    else:
        # Standard web flow redirect URI
        # Check if PUBLIC_URL is set in environment (useful for ngrok/tunnels)
        public_url = os.getenv('PUBLIC_URL')

        if public_url:
            base_url = public_url.rstrip('/')
        else:
            # For development, use localhost:3001 directly since we know the
            # frontend port. In production, this would come from environment
            # variables or proper proxy headers
            base_url_str = str(request.base_url)
            if 'localhost' in base_url_str and ':3001' not in base_url_str:
                # Development mode - frontend is on localhost:3001
                base_url = "http://localhost:3001"
            else:
                # Check for forwarded headers (for production)
                forwarded_host = request.headers.get('x-forwarded-host')
                forwarded_proto = request.headers.get('x-forwarded-proto', 'http')

                if forwarded_host:
                    base_url = f"{forwarded_proto}://{forwarded_host}"
                else:
                    # Fallback to request base URL
                    base_url = str(request.base_url).rstrip('/')

        redirect_uri = (
            f"{base_url}/api/v1/oauth/{tenant_slug}/callback/{provider}"
        )

    print(f"DEBUG: Final redirect_uri = {redirect_uri}")

    # Build authorization URL
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "response_type": "code"
    }

    # Slack uses different parameter names and format
    if provider == "slack":
        params["user_scope"] = ",".join(provider_config["scopes"])  # Comma-separated for Slack
    elif provider == "notion":
        # Notion doesn't use traditional scopes parameter
        pass
    else:
        params["scope"] = " ".join(provider_config["scopes"])  # Space-separated for others

    # Add Google-specific parameters
    if provider in ["google", "google_docs", "google_sheets", "gmail", "google_slides", "google_calendar"]:
        params["access_type"] = "offline"  # Request refresh token
        params["prompt"] = "consent"  # Force consent screen to get refresh token

    auth_url = (
        f"{provider_config['auth_url']}?{urllib.parse.urlencode(params)}"
    )

    # Store state in session or cache (for now, we'll include it in the redirect)
    return RedirectResponse(url=auth_url)


@router.get("/{tenant_slug}/callback/{provider}")
async def oauth_callback(
    tenant_slug: str,
    provider: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session)
):
    """Handle OAuth callback from provider."""
    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported provider: {provider}"
        )

    # Verify tenant exists
    tenant_result = await session.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Get query parameters
    params = dict(request.query_params)

    if "error" in params:
        error = params.get("error", "unknown")
        error_description = params.get(
            "error_description", "No description provided"
        )
        raise HTTPException(
            status_code=400,
            detail=(
                f"OAuth error from {provider}: {error} - "
                f"{error_description}"
            )
        )

    if "code" not in params:
        raise HTTPException(
            status_code=400,
            detail="Authorization code not provided"
        )

    auth_code = params["code"]
    provider_config = OAUTH_PROVIDERS[provider]

    # Check for tenant-specific OAuth configuration first
    tenant_config_result = await session.execute(
        select(OAuthConfig).where(
            OAuthConfig.tenant_id == tenant.id,
            OAuthConfig.provider == provider,
            OAuthConfig.is_active.is_(True)
        )
    )
    tenant_oauth_config = tenant_config_result.scalar_one_or_none()

    # Use tenant config if available, otherwise fall back to global config
    if tenant_oauth_config:
        client_id = tenant_oauth_config.client_id
        client_secret = tenant_oauth_config.client_secret
    else:
        client_id = provider_config["client_id"]
        client_secret = provider_config["client_secret"]

    if not client_id or not client_secret:
        raise HTTPException(
            status_code=500,
            detail=(
                f"OAuth not configured for {provider}. "
                "Please configure OAuth credentials for this tenant."
            )
        )

    # Build redirect URI (must match the one used in initiate_oauth)
    # Check if PUBLIC_URL is set in environment (useful for ngrok/tunnels)
    public_url = os.getenv('PUBLIC_URL')

    if public_url:
        base_url = public_url.rstrip('/')
    else:
        # For development, use localhost:3001 directly since we know the
        # frontend port. In production, this would come from environment
        # variables or proper proxy headers
        base_url_str = str(request.base_url)
        if 'localhost' in base_url_str and ':3001' not in base_url_str:
            # Development mode - frontend is on localhost:3001
            base_url = "http://localhost:3001"
        else:
            # Check for forwarded headers (for production)
            forwarded_host = request.headers.get('x-forwarded-host')
            forwarded_proto = request.headers.get('x-forwarded-proto', 'http')

            if forwarded_host:
                base_url = f"{forwarded_proto}://{forwarded_host}"
            else:
                # Fallback to request base URL
                base_url = str(request.base_url).rstrip('/')

    redirect_uri = (
        f"{base_url}/api/v1/oauth/{tenant_slug}/callback/{provider}"
    )

    # Exchange authorization code for access token
    token_data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": auth_code,
        "redirect_uri": redirect_uri,
    }

    # Google, Atlassian, Microsoft, Notion, and Zoom OAuth require grant_type parameter
    if provider in ["google", "google_docs", "google_sheets", "gmail", "google_slides", "google_calendar", "microsoft", "teams", "excel", "outlook", "powerpoint", "jira", "confluence", "notion", "zoom", "gitlab", "bitbucket", "linear", "discord"]:
        token_data["grant_type"] = "authorization_code"

    headers = {"Accept": "application/json"}

    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            provider_config["token_url"],
            data=token_data,
            headers=headers
        )

        if token_response.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Failed to exchange authorization code: "
                    f"{token_response.text}"
                )
            )

        token_info = token_response.json()

    access_token = token_info.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="No access token received")

    # Get user information from provider
    user_headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient() as client:
        if provider == "linear":
            # Linear uses GraphQL for user info
            user_response = await client.post(
                provider_config["user_url"],
                json={"query": "{ viewer { id name email } }"},
                headers={**user_headers, "Content-Type": "application/json"}
            )
        else:
            user_response = await client.get(
                provider_config["user_url"],
                headers=user_headers
            )

        if user_response.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Failed to get user info: {user_response.text}"
                )
            )

        user_info = user_response.json()

    # Extract user data based on provider
    if provider == "github":
        provider_user_id = str(user_info["id"])
        provider_username = user_info["login"]
    elif provider == "slack":
        # Slack OAuth v2 returns user_id in the auth.test response
        provider_user_id = user_info.get("user_id", user_info.get("user"))
        provider_username = user_info.get("user", provider_user_id)
    elif provider in ["google", "google_docs", "google_sheets", "gmail", "google_slides", "google_calendar"]:
        # Google OAuth returns 'id' and 'email' fields
        provider_user_id = str(user_info.get("id", user_info.get("sub", "unknown")))
        provider_username = user_info.get("email", user_info.get("name", "unknown"))
    elif provider in ["microsoft", "teams", "excel", "outlook", "powerpoint"]:
        # Microsoft Graph /me returns 'id', 'mail' or 'userPrincipalName'
        provider_user_id = str(user_info.get("id", "unknown"))
        provider_username = user_info.get("mail", user_info.get("userPrincipalName", "unknown"))
    elif provider in ["jira", "confluence"]:
        # Atlassian OAuth returns 'account_id' and 'email' fields
        provider_user_id = str(user_info.get("account_id", "unknown"))
        provider_username = user_info.get("email", user_info.get("name", "unknown"))
    elif provider == "gitlab":
        # GitLab OAuth returns 'id' and 'username' fields
        provider_user_id = str(user_info.get("id", "unknown"))
        provider_username = user_info.get("username", user_info.get("email", "unknown"))
    elif provider == "bitbucket":
        # Bitbucket OAuth returns 'uuid' and 'username' or 'display_name'
        provider_user_id = str(user_info.get("uuid", user_info.get("account_id", "unknown")))
        provider_username = user_info.get("username", user_info.get("display_name", "unknown"))
    elif provider == "notion":
        # Notion OAuth returns user object with 'id' field
        user_obj = user_info.get("bot", {}).get("owner", {}).get("user", user_info)
        provider_user_id = str(user_obj.get("id", "unknown"))
        provider_username = user_obj.get("name", user_obj.get("person", {}).get("email", "unknown"))
    elif provider == "zoom":
        # Zoom OAuth returns 'id' and 'email' fields
        provider_user_id = str(user_info.get("id", "unknown"))
        provider_username = user_info.get("email", user_info.get("first_name", "unknown"))
    elif provider == "linear":
        # Linear GraphQL viewer returns { data: { viewer: { id, name, email } } }
        viewer = user_info.get("data", {}).get("viewer", {})
        provider_user_id = str(viewer.get("id", "unknown"))
        provider_username = viewer.get("email", viewer.get("name", "unknown"))
    elif provider == "discord":
        # Discord /users/@me returns 'id' and 'username'
        provider_user_id = str(user_info.get("id", "unknown"))
        provider_username = user_info.get("username", user_info.get("global_name", "unknown"))
    else:
        provider_user_id = str(user_info.get("id", "unknown"))
        provider_username = user_info.get(
            "login", user_info.get("username", "unknown")
        )

    # Calculate expiration time
    expires_at = None
    if "expires_in" in token_info:
        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=int(token_info["expires_in"])
        )

    # Check if credential already exists for this tenant/provider/user
    existing_cred = await session.execute(
        select(OAuthCredential).where(
            OAuthCredential.tenant_id == tenant.id,
            OAuthCredential.provider == provider,
            OAuthCredential.provider_user_id == provider_user_id
        )
    )
    existing = existing_cred.scalar_one_or_none()

    if existing:
        # Update existing credential
        existing.access_token = access_token
        existing.refresh_token = token_info.get("refresh_token")
        existing.token_type = token_info.get("token_type", "bearer")
        existing.expires_at = expires_at
        existing.scopes = token_info.get("scope")
        existing.provider_data = str(user_info)
        existing.is_active = True
        existing.updated_at = datetime.now(timezone.utc)
    else:
        # Create new credential
        oauth_cred = OAuthCredential(
            tenant_id=tenant.id,
            provider=provider,
            provider_user_id=provider_user_id,
            provider_username=provider_username,
            access_token=access_token,
            refresh_token=token_info.get("refresh_token"),
            token_type=token_info.get("token_type", "bearer"),
            expires_at=expires_at,
            scopes=token_info.get("scope"),
            provider_data=str(user_info),
            is_active=True
        )
        session.add(oauth_cred)

    await session.commit()

    # Check if this is a CLI session by examining the state parameter
    # CLI sessions include a cli_session parameter in the state
    state_param = params.get("state", "")
    cli_session_id = None

    print(f"DEBUG: Callback received state parameter: '{state_param}'")
    print(f"DEBUG: Full query params: {params}")

    # Try to extract cli_session from state parameter
    # State could be JSON encoded or contain cli_session directly
    if state_param:
        try:
            # Try parsing as JSON first (for structured state)
            import json
            import base64
            try:
                decoded = base64.urlsafe_b64decode(state_param + "==").decode()
                state_data = json.loads(decoded)
                cli_session_id = state_data.get("cli_session")
                print(f"DEBUG: Extracted cli_session from JSON: {cli_session_id}")
            except Exception as e:
                # Not base64/JSON, check if state itself contains cli-session prefix
                print(f"DEBUG: Not base64/JSON (error: {e}), checking for cli-session prefix")
                if state_param.startswith("cli-session-"):
                    cli_session_id = state_param
                    print(f"DEBUG: Found CLI session ID: {cli_session_id}")
                else:
                    print(f"DEBUG: State does not start with 'cli-session-': '{state_param[:50]}'")
        except Exception as e:
            print(f"DEBUG: Outer exception: {e}")
            pass

    # If this is a CLI session, store the result for polling
    if cli_session_id:
        from sage_mcp.utils.cli_session_storage import cli_session_storage

        print(f"DEBUG: Storing CLI session result for session ID: {cli_session_id}")

        # Store successful OAuth result
        session_data = {
            "status": "success",
            "provider": provider,
            "provider_user_id": provider_user_id,
            "provider_username": provider_username,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "scopes": token_info.get("scope"),
            "is_active": True,
            "tenant_slug": tenant_slug
        }
        cli_session_storage.store(cli_session_id, session_data)
        print(f"DEBUG: Successfully stored session data: {session_data}")

        # For CLI sessions, return simple success page instead of redirecting to frontend
        html = f"""
        <html>
            <head><title>OAuth Success</title></head>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h1 style="color: #4caf50;">✅ Authorization Successful</h1>
                <p style="font-size: 18px;">
                    You have successfully authorized <strong>{provider}</strong> for tenant <strong>{tenant_slug}</strong>
                </p>
                <p style="color: #666;">
                    Authorized as: <strong>{provider_username}</strong>
                </p>
                <hr style="margin: 30px auto; width: 300px;">
                <p style="font-size: 16px; color: #333;">
                    You can close this window and return to your terminal.
                </p>
                <p style="color: #999; font-size: 14px;">
                    The SageMCP CLI has been notified and will continue automatically.
                </p>
            </body>
        </html>
        """
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html)
    else:
        print("DEBUG: Not a CLI session (cli_session_id is None)")

    # Standard web flow: Redirect to frontend with success message
    # Use same logic as redirect URI generation for consistency
    public_url = os.getenv('PUBLIC_URL')

    if public_url:
        frontend_url = public_url.rstrip('/')
    else:
        base_url_str = str(request.base_url)
        if 'localhost' in base_url_str and ':3001' not in base_url_str:
            # Development mode - frontend is on localhost:3001
            frontend_url = "http://localhost:3001"
        else:
            # Check for forwarded headers (for production)
            forwarded_host = request.headers.get('x-forwarded-host')
            forwarded_proto = request.headers.get('x-forwarded-proto', 'http')

            if forwarded_host:
                frontend_url = f"{forwarded_proto}://{forwarded_host}"
            else:
                # Fallback to request base URL, try to replace 8000 with 3001
                frontend_url = base_url_str.rstrip('/').replace(':8000', ':3001')

    success_url = (
        f"{frontend_url}/oauth/success?provider={provider}&"
        f"tenant={tenant_slug}"
    )
    print(f"DEBUG: OAuth success redirect URL = {success_url}")

    return RedirectResponse(url=success_url)


@router.delete("/{tenant_slug}/auth/{provider}")
async def revoke_oauth(
    tenant_slug: str,
    provider: str,
    session: AsyncSession = Depends(get_db_session)
):
    """Revoke OAuth credentials for a provider."""
    # Verify tenant exists
    tenant_result = await session.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Delete OAuth credentials for this tenant and provider
    result = await session.execute(
        delete(OAuthCredential).where(
            OAuthCredential.tenant_id == tenant.id,
            OAuthCredential.provider == provider
        )
    )

    await session.commit()

    if result.rowcount == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No OAuth credentials found for {provider}"
        )

    return {
        "message": f"OAuth credentials revoked for {provider}",
        "tenant": tenant_slug,
        "provider": provider,
        "revoked_count": result.rowcount
    }


@router.get(
    "/{tenant_slug}/auth",
    response_model=List[OAuthCredentialResponse]
)
async def list_oauth_credentials(
    tenant_slug: str,
    session: AsyncSession = Depends(get_db_session)
):
    """List OAuth credentials for a tenant."""
    # Verify tenant exists
    tenant_result = await session.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Get OAuth credentials for this tenant
    credentials_result = await session.execute(
        select(OAuthCredential).where(
            OAuthCredential.tenant_id == tenant.id
        )
    )
    credentials = credentials_result.scalars().all()

    return list(credentials)


@router.get("/providers")
async def list_oauth_providers():
    """List available OAuth providers and their configuration status."""
    providers = []
    for provider_id, config in OAUTH_PROVIDERS.items():
        providers.append({
            "id": provider_id,
            "name": config["name"],
            "scopes": config["scopes"],
            "configured": bool(config["client_id"] and config["client_secret"]),
            "auth_url": config["auth_url"]
        })

    return providers


@router.get("/{tenant_slug}/config")
async def list_oauth_configs(
    tenant_slug: str,
    session: AsyncSession = Depends(get_db_session)
):
    """List OAuth configurations for a tenant."""
    # Verify tenant exists
    tenant_result = await session.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Get OAuth configurations
    configs_result = await session.execute(
        select(OAuthConfig).where(OAuthConfig.tenant_id == tenant.id)
    )
    configs = configs_result.scalars().all()

    return list(configs)


@router.post("/{tenant_slug}/config")
async def create_oauth_config(
    tenant_slug: str,
    config_data: OAuthConfigCreate,
    session: AsyncSession = Depends(get_db_session)
):
    """Create or update OAuth configuration for a tenant."""
    # Verify tenant exists
    tenant_result = await session.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Validate provider
    if config_data.provider not in OAUTH_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported provider: {config_data.provider}"
        )

    # Check if configuration already exists
    existing_config = await session.execute(
        select(OAuthConfig).where(
            OAuthConfig.tenant_id == tenant.id,
            OAuthConfig.provider == config_data.provider
        )
    )
    existing = existing_config.scalar_one_or_none()

    if existing:
        # Update existing configuration
        existing.client_id = config_data.client_id
        existing.client_secret = config_data.client_secret
        existing.is_active = True
        await session.commit()
        await session.refresh(existing)
        return existing
    else:
        # Create new configuration
        new_config = OAuthConfig(
            tenant_id=tenant.id,
            provider=config_data.provider,
            client_id=config_data.client_id,
            client_secret=config_data.client_secret
        )
        session.add(new_config)
        await session.commit()
        await session.refresh(new_config)
        return new_config


@router.delete("/{tenant_slug}/config/{provider}")
async def delete_oauth_config(
    tenant_slug: str,
    provider: str,
    session: AsyncSession = Depends(get_db_session)
):
    """Delete OAuth configuration for a tenant and provider."""
    # Verify tenant exists
    tenant_result = await session.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Find and delete configuration
    config_result = await session.execute(
        select(OAuthConfig).where(
            OAuthConfig.tenant_id == tenant.id,
            OAuthConfig.provider == provider
        )
    )
    config = config_result.scalar_one_or_none()

    if not config:
        raise HTTPException(
            status_code=404,
            detail="OAuth configuration not found"
        )

    await session.delete(config)
    await session.commit()

    return {
        "message": (
            f"OAuth configuration for {provider} deleted successfully"
        )
    }


@router.get("/cli-sessions/{session_id}")
async def get_cli_session_result(session_id: str):
    """Get OAuth result for CLI session.

    This endpoint allows CLI clients to poll for OAuth authorization results.
    The session is created when the OAuth flow is initiated with a cli_session
    parameter in the state, and the result is stored when the callback completes.

    Args:
        session_id: CLI session identifier

    Returns:
        OAuth result data including status, provider info, and credentials

    Raises:
        HTTPException: If session not found or expired
    """
    from sage_mcp.utils.cli_session_storage import cli_session_storage

    print(f"DEBUG: Polling for CLI session ID: {session_id}")

    # Get storage stats for debugging
    stats = cli_session_storage.get_stats()
    print(f"DEBUG: Session storage stats: {stats}")

    result = cli_session_storage.get(session_id, delete_after_read=True)

    if not result:
        print(f"DEBUG: Session not found or expired: {session_id}")
        raise HTTPException(
            status_code=404,
            detail="Session not found or expired. It may have already been retrieved or timed out after 5 minutes."
        )

    print(f"DEBUG: Found session result: {result}")
    return result

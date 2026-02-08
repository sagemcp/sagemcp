"""Configuration management for Sage MCP."""

import os
from functools import lru_cache
from typing import List, Optional, Union, Literal

from pydantic import Field, field_validator, ConfigDict
from pydantic_settings import BaseSettings
from pydantic_core import Url


class Settings(BaseSettings):
    """Application settings."""

    model_config = ConfigDict(
        env_file=".env" if os.getenv("ENVIRONMENT") != "test" else None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"
    )

    # Application
    app_name: str = "Sage MCP"
    app_version: str = "0.1.0"
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")

    # Server
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")

    # Database
    database_provider: Literal["postgresql", "supabase"] = Field(
        default="postgresql", env="DATABASE_PROVIDER"
    )
    database_url: str = Field(
        default="postgresql://sage_mcp:password@localhost:5432/sage_mcp",
        env="DATABASE_URL"
    )

    # Supabase specific configuration
    supabase_url: Optional[str] = Field(default=None, env="SUPABASE_URL")
    supabase_anon_key: Optional[str] = Field(default=None, env="SUPABASE_ANON_KEY")
    supabase_service_role_key: Optional[str] = Field(default=None, env="SUPABASE_SERVICE_ROLE_KEY")
    supabase_database_password: Optional[str] = Field(default=None, env="SUPABASE_DATABASE_PASSWORD")

    # Security
    secret_key: str = Field(env="SECRET_KEY")
    access_token_expire_minutes: int = Field(
        default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    refresh_token_expire_days: int = Field(
        default=7, env="REFRESH_TOKEN_EXPIRE_DAYS"
    )

    # OAuth Configuration
    github_client_id: Optional[str] = Field(
        default=None, env="GITHUB_CLIENT_ID"
    )
    github_client_secret: Optional[str] = Field(
        default=None, env="GITHUB_CLIENT_SECRET"
    )

    gitlab_client_id: Optional[str] = Field(
        default=None, env="GITLAB_CLIENT_ID"
    )
    gitlab_client_secret: Optional[str] = Field(
        default=None, env="GITLAB_CLIENT_SECRET"
    )

    google_client_id: Optional[str] = Field(
        default=None, env="GOOGLE_CLIENT_ID"
    )
    google_client_secret: Optional[str] = Field(
        default=None, env="GOOGLE_CLIENT_SECRET"
    )

    # Google API Scopes
    google_docs_scopes: str = Field(
        default="https://www.googleapis.com/auth/documents https://www.googleapis.com/auth/drive.readonly https://www.googleapis.com/auth/drive.file",
        env="GOOGLE_DOCS_SCOPES"
    )

    # OAuth Configuration - Notion
    notion_client_id: Optional[str] = Field(
        default=None, env="NOTION_CLIENT_ID"
    )
    notion_client_secret: Optional[str] = Field(
        default=None, env="NOTION_CLIENT_SECRET"
    )

    # OAuth Configuration - Zoom
    zoom_client_id: Optional[str] = Field(
        default=None, env="ZOOM_CLIENT_ID"
    )
    zoom_client_secret: Optional[str] = Field(
        default=None, env="ZOOM_CLIENT_SECRET"
    )

    # OAuth Configuration - Microsoft
    microsoft_client_id: Optional[str] = Field(
        default=None, env="MICROSOFT_CLIENT_ID"
    )
    microsoft_client_secret: Optional[str] = Field(
        default=None, env="MICROSOFT_CLIENT_SECRET"
    )

    # OAuth Configuration - Bitbucket
    bitbucket_client_id: Optional[str] = Field(
        default=None, env="BITBUCKET_CLIENT_ID"
    )
    bitbucket_client_secret: Optional[str] = Field(
        default=None, env="BITBUCKET_CLIENT_SECRET"
    )

    # OAuth Configuration - Jira
    jira_client_id: Optional[str] = Field(
        default=None, env="JIRA_CLIENT_ID"
    )
    jira_client_secret: Optional[str] = Field(
        default=None, env="JIRA_CLIENT_SECRET"
    )

    # OAuth Configuration - Linear
    linear_client_id: Optional[str] = Field(
        default=None, env="LINEAR_CLIENT_ID"
    )
    linear_client_secret: Optional[str] = Field(
        default=None, env="LINEAR_CLIENT_SECRET"
    )

    # OAuth Configuration - Discord
    discord_client_id: Optional[str] = Field(
        default=None, env="DISCORD_CLIENT_ID"
    )
    discord_client_secret: Optional[str] = Field(
        default=None, env="DISCORD_CLIENT_SECRET"
    )

    # Base URL for OAuth redirects
    base_url: str = Field(default="http://localhost:8000", env="BASE_URL")

    # MCP Configuration
    mcp_server_timeout: int = Field(default=30, env="MCP_SERVER_TIMEOUT")
    mcp_max_connections_per_tenant: int = Field(
        default=10, env="MCP_MAX_CONNECTIONS_PER_TENANT"
    )
    mcp_allowed_origins: Optional[str] = Field(
        default=None,
        env="MCP_ALLOWED_ORIGINS",
        description="Comma-separated list of allowed origins for MCP requests",
    )

    # Image Registry Configuration
    image_registry: Optional[str] = Field(
        default="localhost:5000", env="IMAGE_REGISTRY"
    )

    # Redis Configuration
    redis_url: Optional[str] = Field(
        default=None, env="REDIS_URL"
    )

    # CORS Configuration
    cors_allowed_origins: Optional[str] = Field(
        default=None,
        env="CORS_ALLOWED_ORIGINS",
        description="Comma-separated list of allowed CORS origins. Defaults to ['*'] in dev.",
    )

    # Rate Limiting
    rate_limit_rpm: int = Field(
        default=100,
        env="RATE_LIMIT_RPM",
        description="Default requests per minute per tenant",
    )

    # Feature Flags
    enable_server_pool: bool = Field(default=False, env="SAGEMCP_ENABLE_SERVER_POOL")
    enable_session_management: bool = Field(default=False, env="SAGEMCP_ENABLE_SESSION_MANAGEMENT")
    enable_metrics: bool = Field(default=False, env="SAGEMCP_ENABLE_METRICS")

    @field_validator("secret_key", mode="before")
    @classmethod
    def validate_secret_key(cls, v):
        if not v:
            # Generate a random secret key for development
            import secrets
            return secrets.token_urlsafe(32)
        return v

    @field_validator("database_url", mode="before")
    @classmethod
    def validate_database_url(cls, v):
        # Allow SQLite URLs for testing
        url = str(v)
        if url.startswith(("sqlite://", "sqlite+aiosqlite://")):
            return url
        return url

    def get_database_url(self) -> str:
        """Get the appropriate database URL based on the provider."""
        if self.database_provider == "supabase":
            if self.supabase_url:
                import re
                match = re.match(r'https://([^.]+)\.supabase\.co', self.supabase_url)
                if match:
                    project_id = match.group(1)
                    password = self.supabase_database_password or self.supabase_service_role_key or "postgres"
                    return f"postgresql://postgres.{project_id}:{password}@aws-0-us-west-1.pooler.supabase.com:5432/postgres"

            return self.database_url

        return self.database_url

    def get_cors_origins(self) -> List[str]:
        """Parse CORS allowed origins from config."""
        if self.cors_allowed_origins:
            return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]
        # Default: allow all in development
        if self.environment != "production":
            return ["*"]
        return []

    def get_mcp_allowed_origins(self) -> Optional[List[str]]:
        """Parse MCP allowed origins from config."""
        if self.mcp_allowed_origins:
            return [o.strip() for o in self.mcp_allowed_origins.split(",") if o.strip()]
        return None


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()

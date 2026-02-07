"""Admin API for platform settings (read-only view of non-secret config)."""

from fastapi import APIRouter, Request

from ..config import get_settings

router = APIRouter()


@router.get("/settings")
async def get_platform_settings(request: Request):
    """Return non-secret platform configuration."""
    settings = get_settings()

    pool = getattr(request.app.state, "server_pool", None)
    sm = getattr(request.app.state, "session_manager", None)

    return {
        "platform": {
            "app_name": settings.app_name,
            "app_version": settings.app_version,
            "environment": settings.environment,
            "debug": settings.debug,
        },
        "features": {
            "server_pool": settings.enable_server_pool,
            "session_management": settings.enable_session_management,
            "metrics": settings.enable_metrics,
        },
        "pool": {
            "max_size": pool.max_size if pool else 0,
            "ttl_seconds": pool.ttl_seconds if pool else 0,
            "current_size": pool.size if pool else 0,
        },
        "rate_limit": {
            "rpm": settings.rate_limit_rpm,
        },
        "cors": {
            "origins": settings.get_cors_origins(),
        },
        "mcp": {
            "server_timeout": settings.mcp_server_timeout,
            "max_connections_per_tenant": settings.mcp_max_connections_per_tenant,
            "allowed_origins": settings.get_mcp_allowed_origins(),
        },
        "database": {
            "provider": settings.database_provider,
        },
        "sessions": {
            "active": len(sm.sessions) if sm else 0,
        },
    }

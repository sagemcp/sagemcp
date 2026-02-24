"""Main FastAPI application for Sage MCP."""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from .api.routes import router as api_router
from .config import get_settings
from .database.connection import db_manager
from .database.migrations import (
    create_tables,
    upgrade_add_external_mcp_runtime,
    upgrade_add_custom_connector_type,
    upgrade_add_runtime_type_values,
    upgrade_add_process_status_values,
    upgrade_remove_connector_unique_constraint,
    upgrade_add_mcp_server_registry,
    upgrade_encrypt_existing_secrets,
    upgrade_create_api_keys_table,
)
from .observability.logging import configure_logging

# Import connectors to register them
from .connectors import github  # noqa

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    settings = get_settings()

    # Configure structured logging
    configure_logging(
        environment=settings.environment,
        log_level="DEBUG" if settings.debug else "INFO",
    )

    # Initialize database
    db_manager.initialize()

    # Create tables if they don't exist
    await create_tables()

    # Run migrations
    await upgrade_add_external_mcp_runtime()
    await upgrade_add_custom_connector_type()
    await upgrade_add_runtime_type_values()
    await upgrade_add_process_status_values()
    await upgrade_remove_connector_unique_constraint()
    await upgrade_add_mcp_server_registry()

    # Encrypt existing plaintext secrets in DB
    await upgrade_encrypt_existing_secrets()

    # Create api_keys table (Phase 2: API key auth)
    await upgrade_create_api_keys_table()

    # Bootstrap admin API key if auth is enabled and no keys exist
    if settings.enable_auth:
        from .security.auth_bootstrap import bootstrap_admin_key
        await bootstrap_admin_key()

    # Warm up HTTP client (creates connection pool)
    from .connectors.http_client import get_http_client
    get_http_client()

    # Initialize server pool (Phase 1)
    if settings.enable_server_pool:
        from .mcp.pool import ServerPool
        app.state.server_pool = ServerPool()
        logger.info("Server pool enabled (max_size=5000, ttl=1800s)")
    else:
        app.state.server_pool = None

    # Initialize session manager (Phase 2)
    if settings.enable_session_management:
        from .mcp.session import SessionManager
        app.state.session_manager = SessionManager()
        logger.info("Session management enabled")
    else:
        app.state.session_manager = None

    # Initialize event buffer manager (Phase 5)
    from .mcp.event_buffer import EventBufferManager
    app.state.event_buffer_manager = EventBufferManager()

    # Initialize log broadcaster for admin UI streaming
    from .observability.log_broadcaster import LogBroadcaster, BroadcastHandler
    broadcaster = LogBroadcaster()
    app.state.log_broadcaster = broadcaster
    broadcast_handler = BroadcastHandler(broadcaster)
    broadcast_handler.setLevel(logging.INFO)
    logging.getLogger("sage_mcp").addHandler(broadcast_handler)

    # Set MCP allowed origins (Phase 2.4)
    app.state.mcp_allowed_origins = settings.get_mcp_allowed_origins()

    # Initialize and periodically flush in-memory daily tool-call counter.
    from .observability.metrics import (
        bootstrap_tool_calls_today_from_db,
        run_tool_usage_flush_loop,
    )
    await bootstrap_tool_calls_today_from_db()
    app.state.tool_usage_flush_stop = asyncio.Event()
    app.state.tool_usage_flush_task = asyncio.create_task(
        run_tool_usage_flush_loop(app.state.tool_usage_flush_stop, interval_seconds=60.0)
    )

    logger.info("%s v%s started", settings.app_name, settings.app_version)
    logger.info("Environment: %s", settings.environment)
    logger.info("Database: Connected")
    logger.info("HTTP Client: Ready with connection pooling")

    yield

    # Shutdown
    logger.info("Shutting down Sage MCP...")

    # Stop periodic flush loop and persist remaining daily counter increments.
    from .observability.metrics import flush_tool_calls_today_to_db
    flush_stop = getattr(app.state, "tool_usage_flush_stop", None)
    flush_task = getattr(app.state, "tool_usage_flush_task", None)
    if flush_stop is not None:
        flush_stop.set()
    if flush_task is not None:
        await flush_task
    await flush_tool_calls_today_to_db()

    # Shut down server pool
    if app.state.server_pool:
        await app.state.server_pool.shutdown()
        logger.info("Server pool shut down")

    # Shut down session manager
    if app.state.session_manager:
        await app.state.session_manager.shutdown()
        logger.info("Session manager shut down")

    # Terminate all external MCP processes
    from .runtime import process_manager
    await process_manager.terminate_all()
    logger.info("All external MCP processes terminated")

    # Close database connections
    await db_manager.close()
    logger.info("Database connections closed")

    # Close HTTP client and cleanup connections
    from .connectors.http_client import close_http_client
    await close_http_client()
    logger.info("HTTP client closed")

    logger.info("Sage MCP shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Multi-tenant MCP (Model Context Protocol) server platform",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # CORS middleware — configurable origins
    cors_origins = settings.get_cors_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Mcp-Session-Id"],
    )

    # Rate limiting middleware (Phase 4)
    from .middleware.rate_limit import RateLimiter, RateLimitMiddleware
    rate_limiter = RateLimiter(default_rpm=settings.rate_limit_rpm)
    app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter)

    # Include API routes
    app.include_router(api_router, prefix="/api/v1")

    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "description": "Multi-tenant MCP (Model Context Protocol) server platform",
            "environment": settings.environment,
            "endpoints": {
                "health": "/health",
                "docs": "/docs" if settings.debug else "Disabled in production",
                "api": {
                    "admin": "/api/v1/admin",
                    "oauth": "/api/v1/oauth",
                    "registry": "/api/v1/registry",
                    "mcp": "/api/v1/{tenant_slug}/mcp"
                }
            },
            "usage": {
                "create_tenant": "POST /api/v1/admin/tenants",
                "list_tenants": "GET /api/v1/admin/tenants",
                "mcp_websocket": "WS /api/v1/{tenant_slug}/mcp",
                "mcp_http": "POST /api/v1/{tenant_slug}/mcp",
                "mcp_info": "GET /api/v1/{tenant_slug}/mcp/info"
            }
        }

    # Health check endpoints (Phase 3.3)
    @app.get("/health")
    async def health_check():
        """Legacy health check endpoint."""
        return {
            "status": "healthy",
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    @app.get("/health/live")
    async def health_live():
        """Liveness probe — process is running."""
        return {"status": "alive"}

    @app.get("/health/ready")
    async def health_ready(request: Request):
        """Readiness probe — DB reachable, pool initialized."""
        checks = {}

        # Check database
        try:
            from .database.connection import get_db_context
            async with get_db_context() as session:
                from sqlalchemy import text
                await session.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception as e:
            checks["database"] = f"error: {str(e)}"
            return Response(
                content='{"status":"not_ready","checks":' + str(checks).replace("'", '"') + '}',
                status_code=503,
                media_type="application/json",
            )

        # Check pool
        pool = getattr(request.app.state, "server_pool", None)
        if pool:
            checks["server_pool"] = f"ok (size={pool.size})"
        else:
            checks["server_pool"] = "disabled"

        return {"status": "ready", "checks": checks}

    @app.get("/health/startup")
    async def health_startup():
        """Startup probe — migrations complete, connectors registered."""
        from .connectors.registry import connector_registry
        return {
            "status": "started",
            "registered_connectors": connector_registry.list_connectors(),
        }

    # Prometheus metrics endpoint (Phase 3.1)
    if settings.enable_metrics:
        @app.get("/metrics")
        async def metrics_endpoint(request: Request):
            """Prometheus metrics endpoint."""
            from .observability.metrics import generate_metrics_text
            text = generate_metrics_text()
            if text is None:
                return PlainTextResponse("# prometheus_client not installed\n", status_code=501)
            return PlainTextResponse(text, media_type="text/plain; version=0.0.4; charset=utf-8")

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info"
    )

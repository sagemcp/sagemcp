"""Main FastAPI application for Sage MCP."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
)

# Import connectors to register them (connectors/__init__.py imports all)
from . import connectors  # noqa


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    settings = get_settings()

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

    # Warm up HTTP client (creates connection pool)
    from .connectors.http_client import get_http_client
    get_http_client()

    print(f"🚀 {settings.app_name} v{settings.app_version} started")
    print(f"🌍 Environment: {settings.environment}")
    print("🗄️  Database: Connected")
    print("🌐 HTTP Client: Ready with connection pooling")

    yield

    # Shutdown
    print("🛑 Shutting down Sage MCP...")

    # Terminate all external MCP processes
    from .runtime import process_manager
    await process_manager.terminate_all()
    print("✓ All external MCP processes terminated")

    # Close database connections
    await db_manager.close()
    print("✓ Database connections closed")

    # Close HTTP client and cleanup connections
    from .connectors.http_client import close_http_client
    await close_http_client()
    print("✓ HTTP client closed")

    print("👋 Sage MCP shutdown complete")


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

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

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

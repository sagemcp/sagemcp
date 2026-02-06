"""Main API routes for Sage MCP."""

from fastapi import APIRouter

from .admin import router as admin_router
from .admin_logs import router as admin_logs_router
from .admin_pool import router as admin_pool_router
from .admin_sessions import router as admin_sessions_router
from .admin_settings import router as admin_settings_router
from .admin_stats import router as admin_stats_router
from .mcp import router as mcp_router
from .oauth import router as oauth_router
from .registry import router as registry_router

# Main API router
router = APIRouter()

# Include sub-routers
router.include_router(admin_router, prefix="/admin", tags=["admin"])
router.include_router(admin_logs_router, prefix="/admin", tags=["admin"])
router.include_router(admin_pool_router, prefix="/admin", tags=["admin"])
router.include_router(admin_sessions_router, prefix="/admin", tags=["admin"])
router.include_router(admin_settings_router, prefix="/admin", tags=["admin"])
router.include_router(admin_stats_router, prefix="/admin", tags=["admin"])
router.include_router(oauth_router, prefix="/oauth", tags=["oauth"])
router.include_router(registry_router, tags=["registry"])  # Registry routes with full path
router.include_router(mcp_router, prefix="", tags=["mcp"])  # MCP routes at root level

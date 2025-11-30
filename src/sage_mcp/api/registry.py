"""Registry API endpoints for MCP server discovery and marketplace."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_db_session
from ..models.mcp_server_registry import MCPServerRegistry, DiscoveryJob, SourceType, RuntimeType
from ..discovery.manager import discovery_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/registry", tags=["MCP Server Registry"])


# Response Models
class ServerRegistryResponse(BaseModel):
    """Response model for registry server."""

    id: str
    name: str
    display_name: Optional[str]
    description: Optional[str]
    source_type: str
    source_url: str
    npm_package_name: Optional[str] = None
    github_repo: Optional[str] = None
    latest_version: Optional[str]
    runtime_type: str
    runtime_version: Optional[str] = None
    tools_count: int
    resources_count: int
    prompts_count: int
    star_count: int
    download_count: int
    requires_oauth: bool
    oauth_providers: List[str] = Field(default_factory=list)
    author: Optional[str]
    license: Optional[str]
    repository_url: Optional[str]
    homepage_url: Optional[str]
    is_verified: bool
    is_deprecated: bool
    first_discovered_at: str
    last_scanned_at: Optional[str] = None

    class Config:
        """Pydantic config."""
        from_attributes = True


class DiscoveryJobResponse(BaseModel):
    """Response model for discovery job."""

    id: str
    job_type: str
    source: Optional[str]
    status: str
    started_at: str
    completed_at: Optional[str] = None
    servers_found: int
    servers_added: int
    servers_updated: int
    error_message: Optional[str] = None

    class Config:
        """Pydantic config."""
        from_attributes = True


class DiscoveryJobRequest(BaseModel):
    """Request model for triggering discovery."""

    job_type: str = Field("all", description="Job type: npm_scan, github_scan, or all")
    query: str = Field("", description="Search query")
    limit: int = Field(50, description="Maximum results per provider", ge=1, le=100)


class RegistryStatsResponse(BaseModel):
    """Registry statistics response."""

    total_servers: int
    by_runtime: dict
    by_source: dict
    requires_oauth_count: int
    verified_count: int


# API Endpoints
@router.get("/servers", response_model=List[ServerRegistryResponse])
async def list_registry_servers(
    search: Optional[str] = Query(None, description="Search in name/description"),
    runtime_type: Optional[str] = Query(None, description="Filter by runtime"),
    source_type: Optional[str] = Query(None, description="Filter by source"),
    requires_oauth: Optional[bool] = Query(None, description="Filter by OAuth requirement"),
    verified_only: bool = Query(False, description="Show only verified servers"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session)
):
    """List MCP servers in the registry with filtering and pagination.

    Args:
        search: Search query for name/description
        runtime_type: Filter by runtime (nodejs, python, go, rust, binary)
        source_type: Filter by source (npm, github, custom, manual)
        requires_oauth: Filter by OAuth requirement
        verified_only: Show only verified servers
        limit: Maximum results
        offset: Pagination offset
        db: Database session

    Returns:
        List of registry servers
    """
    try:
        query = select(MCPServerRegistry)

        # Apply filters
        if search:
            search_filter = or_(
                MCPServerRegistry.name.ilike(f"%{search}%"),
                MCPServerRegistry.description.ilike(f"%{search}%"),
                MCPServerRegistry.display_name.ilike(f"%{search}%")
            )
            query = query.where(search_filter)

        if runtime_type:
            try:
                runtime_enum = RuntimeType(runtime_type)
                query = query.where(MCPServerRegistry.runtime_type == runtime_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid runtime_type: {runtime_type}")

        if source_type:
            try:
                source_enum = SourceType(source_type)
                query = query.where(MCPServerRegistry.source_type == source_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid source_type: {source_type}")

        if requires_oauth is not None:
            query = query.where(MCPServerRegistry.requires_oauth == requires_oauth)

        if verified_only:
            query = query.where(MCPServerRegistry.is_verified.is_(True))

        # Filter out deprecated servers by default
        query = query.where(MCPServerRegistry.is_deprecated.is_(False))

        # Order by popularity (star count, then download count)
        query = query.order_by(
            MCPServerRegistry.star_count.desc(),
            MCPServerRegistry.download_count.desc()
        )

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = await db.execute(query)
        servers = result.scalars().all()

        return [
            ServerRegistryResponse(
                id=str(server.id),
                name=server.name,
                display_name=server.display_name,
                description=server.description,
                source_type=server.source_type.value,
                source_url=server.source_url,
                npm_package_name=server.npm_package_name,
                github_repo=server.github_repo,
                latest_version=server.latest_version,
                runtime_type=server.runtime_type.value,
                runtime_version=server.runtime_version,
                tools_count=server.tools_count,
                resources_count=server.resources_count,
                prompts_count=server.prompts_count,
                star_count=server.star_count,
                download_count=server.download_count,
                requires_oauth=server.requires_oauth,
                oauth_providers=server.oauth_providers or [],
                author=server.author,
                license=server.license,
                repository_url=server.repository_url,
                homepage_url=server.homepage_url,
                is_verified=server.is_verified,
                is_deprecated=server.is_deprecated,
                first_discovered_at=server.first_discovered_at.isoformat(),
                last_scanned_at=server.last_scanned_at.isoformat() if server.last_scanned_at else None
            )
            for server in servers
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing registry servers: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch registry servers")


@router.get("/servers/{registry_id}", response_model=ServerRegistryResponse)
async def get_registry_server(
    registry_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get detailed information about a registry server.

    Args:
        registry_id: Registry server ID
        db: Database session

    Returns:
        Server details
    """
    try:
        result = await db.execute(
            select(MCPServerRegistry).where(MCPServerRegistry.id == registry_id)
        )
        server = result.scalar_one_or_none()

        if not server:
            raise HTTPException(status_code=404, detail="Server not found in registry")

        return ServerRegistryResponse(
            id=str(server.id),
            name=server.name,
            display_name=server.display_name,
            description=server.description,
            source_type=server.source_type.value,
            source_url=server.source_url,
            npm_package_name=server.npm_package_name,
            github_repo=server.github_repo,
            latest_version=server.latest_version,
            runtime_type=server.runtime_type.value,
            runtime_version=server.runtime_version,
            tools_count=server.tools_count,
            resources_count=server.resources_count,
            prompts_count=server.prompts_count,
            star_count=server.star_count,
            download_count=server.download_count,
            requires_oauth=server.requires_oauth,
            oauth_providers=server.oauth_providers or [],
            author=server.author,
            license=server.license,
            repository_url=server.repository_url,
            homepage_url=server.homepage_url,
            is_verified=server.is_verified,
            is_deprecated=server.is_deprecated,
            first_discovered_at=server.first_discovered_at.isoformat(),
            last_scanned_at=server.last_scanned_at.isoformat() if server.last_scanned_at else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching registry server {registry_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch server details")


@router.get("/stats", response_model=RegistryStatsResponse)
async def get_registry_stats(db: AsyncSession = Depends(get_db_session)):
    """Get registry statistics.

    Args:
        db: Database session

    Returns:
        Registry statistics
    """
    try:
        # Total servers
        total_result = await db.execute(
            select(func.count(MCPServerRegistry.id))
            .where(MCPServerRegistry.is_deprecated.is_(False))
        )
        total_servers = total_result.scalar() or 0

        # By runtime
        runtime_result = await db.execute(
            select(
                MCPServerRegistry.runtime_type,
                func.count(MCPServerRegistry.id)
            )
            .where(MCPServerRegistry.is_deprecated.is_(False))
            .group_by(MCPServerRegistry.runtime_type)
        )
        by_runtime = {row[0].value: row[1] for row in runtime_result}

        # By source
        source_result = await db.execute(
            select(
                MCPServerRegistry.source_type,
                func.count(MCPServerRegistry.id)
            )
            .where(MCPServerRegistry.is_deprecated.is_(False))
            .group_by(MCPServerRegistry.source_type)
        )
        by_source = {row[0].value: row[1] for row in source_result}

        # OAuth count
        oauth_result = await db.execute(
            select(func.count(MCPServerRegistry.id))
            .where(
                MCPServerRegistry.is_deprecated.is_(False),
                MCPServerRegistry.requires_oauth.is_(True)
            )
        )
        requires_oauth_count = oauth_result.scalar() or 0

        # Verified count
        verified_result = await db.execute(
            select(func.count(MCPServerRegistry.id))
            .where(
                MCPServerRegistry.is_deprecated.is_(False),
                MCPServerRegistry.is_verified.is_(True)
            )
        )
        verified_count = verified_result.scalar() or 0

        return RegistryStatsResponse(
            total_servers=total_servers,
            by_runtime=by_runtime,
            by_source=by_source,
            requires_oauth_count=requires_oauth_count,
            verified_count=verified_count
        )

    except Exception as e:
        logger.error(f"Error fetching registry stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch statistics")


@router.post("/discover")
async def trigger_discovery(
    request: DiscoveryJobRequest,
    background_tasks: BackgroundTasks
):
    """Trigger background discovery job.

    Args:
        request: Discovery job parameters
        background_tasks: FastAPI background tasks

    Returns:
        Job ID and status
    """
    try:
        # Validate job type
        valid_types = ["npm_scan", "github_scan", "all"]
        if request.job_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid job_type. Must be one of: {', '.join(valid_types)}"
            )

        # Start discovery job in background
        background_tasks.add_task(
            discovery_manager.run_discovery_job,
            request.job_type,
            request.query,
            request.limit
        )

        # Generate job ID (simplified - in production, return from run_discovery_job)
        from uuid import uuid4
        job_id = str(uuid4())

        logger.info(f"Discovery job triggered: {job_id} (type={request.job_type})")

        return {
            "job_id": job_id,
            "status": "started",
            "message": f"Discovery job started with type: {request.job_type}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering discovery: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger discovery")


@router.get("/discover/jobs/{job_id}", response_model=DiscoveryJobResponse)
async def get_discovery_job_status(
    job_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get discovery job status.

    Args:
        job_id: Job ID
        db: Database session

    Returns:
        Job status
    """
    try:
        result = await db.execute(
            select(DiscoveryJob).where(DiscoveryJob.id == job_id)
        )
        job = result.scalar_one_or_none()

        if not job:
            raise HTTPException(status_code=404, detail="Discovery job not found")

        return DiscoveryJobResponse(
            id=str(job.id),
            job_type=job.job_type,
            source=job.source,
            status=job.status.value,
            started_at=job.started_at.isoformat(),
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
            servers_found=job.servers_found,
            servers_added=job.servers_added,
            servers_updated=job.servers_updated,
            error_message=job.error_message
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching job status {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch job status")


@router.get("/discover/jobs", response_model=List[DiscoveryJobResponse])
async def list_discovery_jobs(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session)
):
    """List recent discovery jobs.

    Args:
        limit: Maximum results
        offset: Pagination offset
        db: Database session

    Returns:
        List of discovery jobs
    """
    try:
        query = (
            select(DiscoveryJob)
            .order_by(DiscoveryJob.started_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await db.execute(query)
        jobs = result.scalars().all()

        return [
            DiscoveryJobResponse(
                id=str(job.id),
                job_type=job.job_type,
                source=job.source,
                status=job.status.value,
                started_at=job.started_at.isoformat(),
                completed_at=job.completed_at.isoformat() if job.completed_at else None,
                servers_found=job.servers_found,
                servers_added=job.servers_added,
                servers_updated=job.servers_updated,
                error_message=job.error_message
            )
            for job in jobs
        ]

    except Exception as e:
        logger.error(f"Error listing discovery jobs: {e}")
        raise HTTPException(status_code=500, detail="Failed to list jobs")


# Installation Endpoints

class InstallServerRequest(BaseModel):
    """Request model for installing a server."""

    tenant_id: str = Field(..., description="Tenant ID")
    config_overrides: Optional[dict] = Field(None, description="Optional configuration overrides")


class InstallationResponse(BaseModel):
    """Response model for installation."""

    success: bool
    connector_id: Optional[str] = None
    message: str


class InstallationStatusResponse(BaseModel):
    """Response model for installation status."""

    connector_id: str
    name: str
    status: str
    container_status: str
    container_ip: Optional[str] = None
    installed_version: Optional[str] = None
    installed_at: Optional[str] = None
    last_health_check: Optional[str] = None


@router.post("/servers/{registry_id}/install", response_model=InstallationResponse)
async def install_server(
    registry_id: UUID,
    request: InstallServerRequest,
    background_tasks: BackgroundTasks
):
    """Install MCP server from registry to tenant.

    This endpoint triggers the installation workflow:
    1. Builds Docker image (if needed)
    2. Creates connector in database
    3. Deploys container/pod
    4. Creates installation record

    Args:
        registry_id: Registry server ID
        request: Installation request with tenant_id and config
        background_tasks: FastAPI background tasks

    Returns:
        Installation response with connector_id or error
    """
    try:
        from ..orchestration.installer import ServerInstaller

        installer = ServerInstaller()

        # Run installation in background
        from uuid import UUID as ParseUUID
        tenant_uuid = ParseUUID(request.tenant_id)

        success, result = await installer.install_server(
            registry_id=registry_id,
            tenant_id=tenant_uuid,
            config_overrides=request.config_overrides
        )

        if success:
            logger.info(f"Server installation successful: {result}")
            return InstallationResponse(
                success=True,
                connector_id=result,
                message="Server installed successfully"
            )
        else:
            logger.error(f"Server installation failed: {result}")
            return InstallationResponse(
                success=False,
                message=f"Installation failed: {result}"
            )

    except Exception as e:
        logger.error(f"Error installing server: {e}")
        raise HTTPException(status_code=500, detail=f"Installation error: {str(e)}")


@router.delete("/installations/{connector_id}")
async def uninstall_server(
    connector_id: UUID,
    tenant_id: str = Query(..., description="Tenant ID")
):
    """Uninstall MCP server.

    Args:
        connector_id: Connector ID
        tenant_id: Tenant ID

    Returns:
        Uninstallation response
    """
    try:
        from ..orchestration.installer import ServerInstaller
        from uuid import UUID as ParseUUID

        installer = ServerInstaller()
        tenant_uuid = ParseUUID(tenant_id)

        success, message = await installer.uninstall_server(
            connector_id=connector_id,
            tenant_id=tenant_uuid
        )

        if success:
            return {"success": True, "message": message}
        else:
            raise HTTPException(status_code=400, detail=message)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uninstalling server: {e}")
        raise HTTPException(status_code=500, detail=f"Uninstallation error: {str(e)}")


@router.get("/installations/{connector_id}/status", response_model=InstallationStatusResponse)
async def get_installation_status(
    connector_id: UUID,
    tenant_id: str = Query(..., description="Tenant ID")
):
    """Get installation status.

    Args:
        connector_id: Connector ID
        tenant_id: Tenant ID

    Returns:
        Installation status
    """
    try:
        from ..orchestration.installer import ServerInstaller
        from uuid import UUID as ParseUUID

        installer = ServerInstaller()
        tenant_uuid = ParseUUID(tenant_id)

        status = await installer.get_installation_status(
            connector_id=connector_id,
            tenant_id=tenant_uuid
        )

        if not status:
            raise HTTPException(status_code=404, detail="Installation not found")

        return InstallationStatusResponse(**status)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching installation status: {e}")
        raise HTTPException(status_code=500, detail=f"Status fetch error: {str(e)}")

"""Discovery manager for coordinating MCP server discovery across providers."""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Dict
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from .base import MCPServerMetadata
from .npm_provider import NPMDiscoveryProvider
from .github_provider import GitHubDiscoveryProvider
from ..database.connection import get_db_context
from ..models.mcp_server_registry import (
    MCPServerRegistry,
    DiscoveryJob,
    JobStatus,
    SourceType,
    RuntimeType,
)

logger = logging.getLogger(__name__)


class DiscoveryManager:
    """Manages MCP server discovery across multiple providers."""

    def __init__(self):
        """Initialize discovery manager with all providers."""
        self.providers = {
            "npm": NPMDiscoveryProvider(),
            "github": GitHubDiscoveryProvider(),
        }

    async def discover_all(self, query: str = "", limit: int = 50) -> List[MCPServerMetadata]:
        """Discover MCP servers from all providers.

        Args:
            query: Search query
            limit: Maximum results per provider

        Returns:
            List of all discovered servers
        """
        logger.info(f"Starting discovery across all providers (query='{query}', limit={limit})")
        all_servers = []

        # Run discovery in parallel across providers
        tasks = [
            provider.search(query, limit)
            for provider in self.providers.values()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            provider_name = list(self.providers.keys())[i]

            if isinstance(result, Exception):
                logger.error(f"Discovery error from {provider_name}: {result}")
                continue

            logger.info(f"Provider {provider_name} returned {len(result)} servers")
            all_servers.extend(result)

        logger.info(f"Total servers discovered: {len(all_servers)}")
        return all_servers

    async def discover_by_provider(
        self,
        provider_name: str,
        query: str = "",
        limit: int = 20
    ) -> List[MCPServerMetadata]:
        """Discover MCP servers from a specific provider.

        Args:
            provider_name: Provider name (npm, github)
            query: Search query
            limit: Maximum results

        Returns:
            List of discovered servers

        Raises:
            ValueError: If provider not found
        """
        if provider_name not in self.providers:
            raise ValueError(f"Unknown provider: {provider_name}")

        provider = self.providers[provider_name]
        logger.info(f"Starting discovery from {provider_name} (query='{query}', limit={limit})")

        servers = await provider.search(query, limit)
        logger.info(f"Provider {provider_name} returned {len(servers)} servers")

        return servers

    async def sync_to_database(self, servers: List[MCPServerMetadata]) -> Dict[str, int]:
        """Sync discovered servers to database registry.

        Args:
            servers: List of discovered servers

        Returns:
            Stats dict with added, updated, skipped counts
        """
        stats = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}

        logger.info(f"Syncing {len(servers)} servers to database")

        async with get_db_context() as session:
            for server in servers:
                try:
                    # Check if server exists (by source_type + source_url)
                    result = await session.execute(
                        select(MCPServerRegistry).where(
                            MCPServerRegistry.source_type == SourceType(server.source_type),
                            MCPServerRegistry.source_url == server.source_url
                        )
                    )
                    existing = result.scalar_one_or_none()

                    if existing:
                        # Update if version changed or it's been more than 24 hours
                        should_update = (
                            existing.latest_version != server.latest_version or
                            (
                                existing.last_scanned_at is None or
                                (datetime.utcnow() - existing.last_scanned_at).days >= 1
                            )
                        )

                        if should_update:
                            await session.execute(
                                update(MCPServerRegistry)
                                .where(MCPServerRegistry.id == existing.id)
                                .values(
                                    latest_version=server.latest_version,
                                    available_versions=server.available_versions,
                                    manifest=server.manifest,
                                    readme=server.readme,
                                    tools_count=server.tools_count,
                                    resources_count=server.resources_count,
                                    prompts_count=server.prompts_count,
                                    star_count=server.star_count,
                                    download_count=server.download_count,
                                    requires_oauth=server.requires_oauth,
                                    oauth_providers=server.oauth_providers,
                                    last_scanned_at=datetime.utcnow(),
                                    last_updated_at=datetime.utcnow()
                                )
                            )
                            stats["updated"] += 1
                            logger.debug(f"Updated server: {server.name}")
                        else:
                            # Just update last_scanned_at
                            await session.execute(
                                update(MCPServerRegistry)
                                .where(MCPServerRegistry.id == existing.id)
                                .values(last_scanned_at=datetime.utcnow())
                            )
                            stats["skipped"] += 1
                            logger.debug(f"Skipped server (no changes): {server.name}")
                    else:
                        # Add new entry
                        new_entry = MCPServerRegistry(
                            id=uuid4(),
                            name=server.name,
                            display_name=server.display_name,
                            description=server.description,
                            source_type=SourceType(server.source_type),
                            source_url=server.source_url,
                            npm_package_name=server.npm_package_name,
                            github_repo=server.github_repo,
                            latest_version=server.latest_version,
                            available_versions=server.available_versions,
                            runtime_type=RuntimeType(server.runtime_type),
                            runtime_version=server.runtime_version,
                            protocol_version=server.protocol_version,
                            supported_protocols=server.supported_protocols,
                            manifest=server.manifest,
                            readme=server.readme,
                            requires_oauth=server.requires_oauth,
                            oauth_providers=server.oauth_providers,
                            oauth_scopes=server.oauth_scopes,
                            tools_count=server.tools_count,
                            resources_count=server.resources_count,
                            prompts_count=server.prompts_count,
                            docker_image=server.docker_image,
                            dockerfile_url=server.dockerfile_url,
                            star_count=server.star_count,
                            download_count=server.download_count,
                            author=server.author,
                            license=server.license,
                            homepage_url=server.homepage_url,
                            repository_url=server.repository_url,
                            documentation_url=server.documentation_url,
                            first_discovered_at=datetime.utcnow(),
                            last_scanned_at=datetime.utcnow(),
                        )
                        session.add(new_entry)
                        stats["added"] += 1
                        logger.debug(f"Added new server: {server.name}")

                except IntegrityError as e:
                    logger.error(f"Database integrity error for {server.name}: {e}")
                    stats["errors"] += 1
                    await session.rollback()
                    continue
                except Exception as e:
                    logger.error(f"Error syncing server {server.name}: {e}")
                    stats["errors"] += 1
                    continue

            # Commit all changes
            await session.commit()

        logger.info(
            f"Sync complete: {stats['added']} added, {stats['updated']} updated, "
            f"{stats['skipped']} skipped, {stats['errors']} errors"
        )
        return stats

    async def run_discovery_job(
        self,
        job_type: str,
        query: str = "",
        limit: int = 50
    ) -> str:
        """Run a background discovery job and track in database.

        Args:
            job_type: Job type (npm_scan, github_scan, all)
            query: Search query
            limit: Maximum results

        Returns:
            Job ID
        """
        job_id = str(uuid4())

        logger.info(f"Starting discovery job {job_id} (type={job_type}, query='{query}')")

        # Create job record
        async with get_db_context() as session:
            job = DiscoveryJob(
                id=job_id,
                job_type=job_type,
                source=query,
                status=JobStatus.RUNNING,
                started_at=datetime.utcnow()
            )
            session.add(job)
            await session.commit()

        try:
            # Run discovery based on job type
            if job_type == "npm_scan":
                servers = await self.discover_by_provider("npm", query, limit)
            elif job_type == "github_scan":
                servers = await self.discover_by_provider("github", query, limit)
            elif job_type == "all":
                servers = await self.discover_all(query, limit)
            else:
                raise ValueError(f"Unknown job type: {job_type}")

            # Sync to database
            stats = await self.sync_to_database(servers)

            # Update job status
            async with get_db_context() as session:
                await session.execute(
                    update(DiscoveryJob)
                    .where(DiscoveryJob.id == job_id)
                    .values(
                        status=JobStatus.COMPLETED,
                        completed_at=datetime.utcnow(),
                        servers_found=len(servers),
                        servers_added=stats["added"],
                        servers_updated=stats["updated"]
                    )
                )
                await session.commit()

            logger.info(f"Discovery job {job_id} completed successfully")

        except Exception as e:
            logger.error(f"Discovery job {job_id} failed: {e}")

            # Update job with error
            async with get_db_context() as session:
                await session.execute(
                    update(DiscoveryJob)
                    .where(DiscoveryJob.id == job_id)
                    .values(
                        status=JobStatus.FAILED,
                        completed_at=datetime.utcnow(),
                        error_message=str(e)
                    )
                )
                await session.commit()

            raise

        return job_id

    async def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get discovery job status.

        Args:
            job_id: Job ID

        Returns:
            Job status dict or None if not found
        """
        async with get_db_context() as session:
            result = await session.execute(
                select(DiscoveryJob).where(DiscoveryJob.id == job_id)
            )
            job = result.scalar_one_or_none()

            if not job:
                return None

            return {
                "id": str(job.id),
                "job_type": job.job_type,
                "source": job.source,
                "status": job.status.value,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "servers_found": job.servers_found,
                "servers_added": job.servers_added,
                "servers_updated": job.servers_updated,
                "error_message": job.error_message
            }


# Global singleton instance
discovery_manager = DiscoveryManager()

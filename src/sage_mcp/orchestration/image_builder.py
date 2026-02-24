"""Image builder service for MCP servers using Kaniko."""

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, Optional
from uuid import uuid4

from ..config import get_settings
from ..models.mcp_server_registry import MCPServerRegistry, RuntimeType
from .base import ContainerConfig
from .factory import get_orchestrator

logger = logging.getLogger(__name__)


@dataclass
class BuildConfig:
    """Configuration for building MCP server images."""

    registry_id: str
    server_name: str
    runtime_type: RuntimeType
    source_url: str
    dockerfile_content: Optional[str] = None
    build_context_url: Optional[str] = None
    env_vars: Dict[str, str] = None

    def __post_init__(self):
        if self.env_vars is None:
            self.env_vars = {}


class ImageBuilder:
    """Builds Docker images for MCP servers using Kaniko."""

    def __init__(self):
        """Initialize image builder."""
        self.settings = get_settings()
        self.orchestrator = get_orchestrator()

    async def build_image(
        self,
        build_config: BuildConfig,
        namespace: str = "sage-mcp-build"
    ) -> tuple[bool, str]:
        """Build Docker image for MCP server.

        Args:
            build_config: Build configuration
            namespace: Namespace for build pod

        Returns:
            Tuple of (success, image_name_or_error)
        """
        build_id = str(uuid4())[:8]
        build_pod_name = f"build-{build_config.server_name}-{build_id}"

        logger.info(
            f"Starting image build for {build_config.server_name} "
            f"(build_id={build_id})"
        )

        try:
            # Generate Dockerfile if not provided
            dockerfile = build_config.dockerfile_content
            if not dockerfile:
                dockerfile = self._generate_dockerfile(build_config)

            # Determine build context
            context_url = build_config.build_context_url or build_config.source_url

            # Generate image name
            image_name = self._generate_image_name(
                build_config.server_name,
                build_config.registry_id
            )

            # Create Kaniko build pod
            success = await self._create_kaniko_pod(
                pod_name=build_pod_name,
                dockerfile=dockerfile,
                context_url=context_url,
                image_name=image_name,
                namespace=namespace
            )

            if not success:
                return False, "Failed to create Kaniko build pod"

            # Wait for build to complete
            success, message = await self._wait_for_build(
                build_pod_name,
                namespace,
                timeout_seconds=600  # 10 minutes
            )

            if success:
                logger.info(f"Image build successful: {image_name}")
                return True, image_name
            else:
                logger.error(f"Image build failed: {message}")
                return False, message

        except Exception as e:
            logger.error(f"Image build error: {e}")
            return False, str(e)

        finally:
            # Cleanup build pod
            try:
                await self.orchestrator.delete_container(build_pod_name, namespace)
            except Exception as e:
                logger.warning(f"Failed to cleanup build pod: {e}")

    def _generate_dockerfile(self, build_config: BuildConfig) -> str:
        """Generate Dockerfile based on runtime type.

        Args:
            build_config: Build configuration

        Returns:
            Dockerfile content
        """
        runtime = build_config.runtime_type

        if runtime == RuntimeType.NODEJS:
            return self._generate_nodejs_dockerfile(build_config)
        elif runtime == RuntimeType.PYTHON:
            return self._generate_python_dockerfile(build_config)
        elif runtime == RuntimeType.GO:
            return self._generate_go_dockerfile(build_config)
        elif runtime == RuntimeType.RUST:
            return self._generate_rust_dockerfile(build_config)
        else:
            raise ValueError(f"Unsupported runtime type: {runtime}")

    def _generate_nodejs_dockerfile(self, build_config: BuildConfig) -> str:
        """Generate Dockerfile for Node.js MCP server."""
        return f"""
FROM node:18-alpine

WORKDIR /app

# Clone or download source
RUN apk add --no-cache git && \\
    git clone {build_config.source_url} /app || \\
    (apk add --no-cache wget && wget -O- {build_config.source_url}/archive/main.tar.gz | tar xz --strip=1)

# Install dependencies
RUN npm install --production

# Expose MCP port (stdio communication doesn't need port)
ENV NODE_ENV=production

# Run MCP server
CMD ["node", "index.js"]
"""

    def _generate_python_dockerfile(self, build_config: BuildConfig) -> str:
        """Generate Dockerfile for Python MCP server."""
        return f"""
FROM python:3.11-slim

WORKDIR /app

# Install git
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Clone or download source
RUN git clone {build_config.source_url} /app || \\
    (apt-get update && apt-get install -y wget && \\
     wget -O- {build_config.source_url}/archive/main.tar.gz | tar xz --strip=1)

# Install dependencies
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi && \\
    if [ -f pyproject.toml ]; then pip install --no-cache-dir .; fi

# Run MCP server
CMD ["python", "-m", "mcp_server"]
"""

    def _generate_go_dockerfile(self, build_config: BuildConfig) -> str:
        """Generate Dockerfile for Go MCP server."""
        return f"""
FROM golang:1.21-alpine AS builder

WORKDIR /app

# Install git
RUN apk add --no-cache git

# Clone source
RUN git clone {build_config.source_url} /app

# Build
RUN go mod download && \\
    go build -o /mcp-server

FROM alpine:latest

WORKDIR /app
COPY --from=builder /mcp-server /app/mcp-server

# Run MCP server
CMD ["/app/mcp-server"]
"""

    def _generate_rust_dockerfile(self, build_config: BuildConfig) -> str:
        """Generate Dockerfile for Rust MCP server."""
        return f"""
FROM rust:1.75-slim AS builder

WORKDIR /app

# Install git
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Clone source
RUN git clone {build_config.source_url} /app

# Build
RUN cargo build --release

FROM debian:bookworm-slim

WORKDIR /app
COPY --from=builder /app/target/release/mcp-server /app/mcp-server

# Run MCP server
CMD ["/app/mcp-server"]
"""

    def _generate_image_name(self, server_name: str, registry_id: str) -> str:
        """Generate Docker image name.

        Args:
            server_name: MCP server name
            registry_id: Registry server ID

        Returns:
            Full image name with registry
        """
        # Clean server name for Docker
        safe_name = server_name.lower().replace("/", "-").replace("@", "")

        # Use configured registry or default to local
        registry = self.settings.image_registry or "localhost:5000"

        return f"{registry}/sage-mcp/{safe_name}:{registry_id[:8]}"

    async def _create_kaniko_pod(
        self,
        pod_name: str,
        dockerfile: str,
        context_url: str,
        image_name: str,
        namespace: str
    ) -> bool:
        """Create Kaniko build pod.

        Args:
            pod_name: Pod name
            dockerfile: Dockerfile content
            context_url: Build context URL
            image_name: Target image name
            namespace: Kubernetes namespace

        Returns:
            True if successful
        """
        try:
            # Kaniko configuration
            kaniko_image = "gcr.io/kaniko-project/executor:latest"

            # Create ConfigMap for Dockerfile
            # (In production, you'd create an actual ConfigMap via K8s API)
            # For now, we'll pass it as an environment variable

            config = ContainerConfig(
                name=pod_name,
                image=kaniko_image,
                args=[
                    f"--context={context_url}",
                    "--dockerfile=Dockerfile",  # Will be created from env
                    f"--destination={image_name}",
                    "--cache=true",
                    "--compressed-caching=false",
                ],
                env={
                    "DOCKERFILE_CONTENT": dockerfile,
                },
                labels={
                    "app": "sage-mcp-builder",
                    "build-type": "kaniko",
                },
                cpu_request="500m",
                cpu_limit="2000m",
                memory_request="512Mi",
                memory_limit="2Gi",
                restart_policy="Never",
            )

            await self.orchestrator.create_container(config, namespace)
            return True

        except Exception as e:
            logger.error(f"Failed to create Kaniko pod: {e}")
            return False

    async def _wait_for_build(
        self,
        pod_name: str,
        namespace: str,
        timeout_seconds: int = 600
    ) -> tuple[bool, str]:
        """Wait for build pod to complete.

        Args:
            pod_name: Pod name
            namespace: Namespace
            timeout_seconds: Timeout in seconds

        Returns:
            Tuple of (success, message)
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            # Check timeout
            if asyncio.get_event_loop().time() - start_time > timeout_seconds:
                return False, "Build timeout exceeded"

            # Get pod status
            info = await self.orchestrator.get_container_status(pod_name, namespace)

            if not info:
                return False, "Build pod not found"

            # Check status
            if info.status.value == "succeeded":
                logs = await self.orchestrator.get_container_logs(
                    pod_name, namespace, tail_lines=50
                )
                return True, logs

            elif info.status.value == "failed":
                logs = await self.orchestrator.get_container_logs(
                    pod_name, namespace, tail_lines=100
                )
                return False, f"Build failed: {info.message}\n\nLogs:\n{logs}"

            elif info.status.value in ["pending", "running"]:
                # Still building, wait and check again
                await asyncio.sleep(5)
                continue

            else:
                return False, f"Unknown build status: {info.status.value}"

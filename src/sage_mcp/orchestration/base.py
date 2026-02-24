"""Base orchestrator interface and data models."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class ContainerStatus(str, Enum):
    """Container/Pod status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class ContainerConfig:
    """Configuration for container/pod deployment."""

    # Identity
    name: str
    image: str

    # Command and environment
    command: Optional[List[str]] = None
    args: Optional[List[str]] = None
    env: Dict[str, str] = field(default_factory=dict)

    # Resources
    cpu_request: str = "100m"
    cpu_limit: str = "500m"
    memory_request: str = "128Mi"
    memory_limit: str = "512Mi"

    # Networking
    ports: List[int] = field(default_factory=list)

    # Labels and annotations
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)

    # Volumes
    volumes: Dict[str, str] = field(default_factory=dict)  # volume_name: mount_path

    # Security
    service_account: Optional[str] = None

    # Restart policy
    restart_policy: str = "Always"


@dataclass
class ContainerInfo:
    """Information about a running container/pod."""

    name: str
    status: ContainerStatus
    image: str
    pod_ip: Optional[str] = None
    host_ip: Optional[str] = None
    started_at: Optional[str] = None
    restart_count: int = 0
    logs_tail: Optional[str] = None
    message: Optional[str] = None


class BaseOrchestrator(ABC):
    """Abstract base class for container orchestration."""

    @abstractmethod
    async def create_container(
        self,
        config: ContainerConfig,
        namespace: str = "default"
    ) -> str:
        """Create a new container/pod.

        Args:
            config: Container configuration
            namespace: Kubernetes namespace or Docker network

        Returns:
            Container/Pod ID
        """
        pass

    @abstractmethod
    async def delete_container(
        self,
        name: str,
        namespace: str = "default"
    ) -> bool:
        """Delete a container/pod.

        Args:
            name: Container/Pod name
            namespace: Kubernetes namespace or Docker network

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def get_container_status(
        self,
        name: str,
        namespace: str = "default"
    ) -> Optional[ContainerInfo]:
        """Get container/pod status.

        Args:
            name: Container/Pod name
            namespace: Kubernetes namespace or Docker network

        Returns:
            Container information or None if not found
        """
        pass

    @abstractmethod
    async def list_containers(
        self,
        namespace: str = "default",
        labels: Optional[Dict[str, str]] = None
    ) -> List[ContainerInfo]:
        """List containers/pods.

        Args:
            namespace: Kubernetes namespace or Docker network
            labels: Filter by labels

        Returns:
            List of container information
        """
        pass

    @abstractmethod
    async def get_container_logs(
        self,
        name: str,
        namespace: str = "default",
        tail_lines: int = 100,
        follow: bool = False
    ) -> str:
        """Get container/pod logs.

        Args:
            name: Container/Pod name
            namespace: Kubernetes namespace or Docker network
            tail_lines: Number of lines to return from end
            follow: Stream logs in real-time

        Returns:
            Log output
        """
        pass

    @abstractmethod
    async def restart_container(
        self,
        name: str,
        namespace: str = "default"
    ) -> bool:
        """Restart a container/pod.

        Args:
            name: Container/Pod name
            namespace: Kubernetes namespace or Docker network

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def exec_command(
        self,
        name: str,
        command: List[str],
        namespace: str = "default"
    ) -> tuple[str, str]:
        """Execute command in container/pod.

        Args:
            name: Container/Pod name
            command: Command to execute
            namespace: Kubernetes namespace or Docker network

        Returns:
            Tuple of (stdout, stderr)
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if orchestrator is available and healthy.

        Returns:
            True if healthy
        """
        pass

"""Kubernetes orchestrator implementation."""

import logging
from typing import Dict, List, Optional

from kubernetes_asyncio import client, config
from kubernetes_asyncio.client.exceptions import ApiException
from kubernetes_asyncio.stream import WsApiClient

from .base import BaseOrchestrator, ContainerConfig, ContainerInfo, ContainerStatus

logger = logging.getLogger(__name__)


class KubernetesOrchestrator(BaseOrchestrator):
    """Kubernetes-based orchestrator for managing MCP server pods."""

    def __init__(self):
        """Initialize Kubernetes orchestrator."""
        self.api_client: Optional[client.ApiClient] = None
        self.core_v1: Optional[client.CoreV1Api] = None
        self._initialized = False

    async def _ensure_initialized(self):
        """Ensure Kubernetes client is initialized."""
        if self._initialized:
            return

        try:
            # Try in-cluster config first (for production)
            try:
                config.load_incluster_config()
                logger.info("Loaded in-cluster Kubernetes configuration")
            except config.ConfigException:
                # Fall back to kubeconfig (for local development)
                await config.load_kube_config()
                logger.info("Loaded Kubernetes configuration from kubeconfig")

            self.api_client = client.ApiClient()
            self.core_v1 = client.CoreV1Api(self.api_client)
            self._initialized = True

        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes client: {e}")
            raise

    def _convert_status(self, phase: str) -> ContainerStatus:
        """Convert Kubernetes pod phase to ContainerStatus.

        Args:
            phase: Kubernetes pod phase

        Returns:
            ContainerStatus enum value
        """
        status_map = {
            "Pending": ContainerStatus.PENDING,
            "Running": ContainerStatus.RUNNING,
            "Succeeded": ContainerStatus.SUCCEEDED,
            "Failed": ContainerStatus.FAILED,
            "Unknown": ContainerStatus.UNKNOWN,
        }
        return status_map.get(phase, ContainerStatus.UNKNOWN)

    async def create_container(
        self,
        config: ContainerConfig,
        namespace: str = "default"
    ) -> str:
        """Create a new Kubernetes pod.

        Args:
            config: Container configuration
            namespace: Kubernetes namespace

        Returns:
            Pod name
        """
        await self._ensure_initialized()

        # Build container spec
        container = client.V1Container(
            name=config.name,
            image=config.image,
            command=config.command,
            args=config.args,
            env=[
                client.V1EnvVar(name=key, value=value)
                for key, value in config.env.items()
            ],
            resources=client.V1ResourceRequirements(
                requests={
                    "cpu": config.cpu_request,
                    "memory": config.memory_request,
                },
                limits={
                    "cpu": config.cpu_limit,
                    "memory": config.memory_limit,
                }
            ),
            ports=[
                client.V1ContainerPort(container_port=port)
                for port in config.ports
            ] if config.ports else None,
            volume_mounts=[
                client.V1VolumeMount(name=vol_name, mount_path=mount_path)
                for vol_name, mount_path in config.volumes.items()
            ] if config.volumes else None,
        )

        # Build pod spec
        pod_spec = client.V1PodSpec(
            containers=[container],
            restart_policy=config.restart_policy,
            service_account_name=config.service_account,
            volumes=[
                client.V1Volume(
                    name=vol_name,
                    empty_dir=client.V1EmptyDirVolumeSource()
                )
                for vol_name in config.volumes.keys()
            ] if config.volumes else None,
        )

        # Build pod metadata
        metadata = client.V1ObjectMeta(
            name=config.name,
            labels=config.labels or {},
            annotations=config.annotations or {},
        )

        # Create pod object
        pod = client.V1Pod(
            api_version="v1",
            kind="Pod",
            metadata=metadata,
            spec=pod_spec,
        )

        try:
            # Create pod in Kubernetes
            result = await self.core_v1.create_namespaced_pod(
                namespace=namespace,
                body=pod
            )
            logger.info(f"Created pod {config.name} in namespace {namespace}")
            return result.metadata.name

        except ApiException as e:
            logger.error(f"Failed to create pod {config.name}: {e}")
            raise

    async def delete_container(
        self,
        name: str,
        namespace: str = "default"
    ) -> bool:
        """Delete a Kubernetes pod.

        Args:
            name: Pod name
            namespace: Kubernetes namespace

        Returns:
            True if successful
        """
        await self._ensure_initialized()

        try:
            await self.core_v1.delete_namespaced_pod(
                name=name,
                namespace=namespace,
                grace_period_seconds=5
            )
            logger.info(f"Deleted pod {name} in namespace {namespace}")
            return True

        except ApiException as e:
            if e.status == 404:
                logger.warning(f"Pod {name} not found in namespace {namespace}")
                return True
            logger.error(f"Failed to delete pod {name}: {e}")
            return False

    async def get_container_status(
        self,
        name: str,
        namespace: str = "default"
    ) -> Optional[ContainerInfo]:
        """Get Kubernetes pod status.

        Args:
            name: Pod name
            namespace: Kubernetes namespace

        Returns:
            Container information or None if not found
        """
        await self._ensure_initialized()

        try:
            pod = await self.core_v1.read_namespaced_pod(
                name=name,
                namespace=namespace
            )

            status = self._convert_status(pod.status.phase)
            container_status = pod.status.container_statuses[0] if pod.status.container_statuses else None

            return ContainerInfo(
                name=pod.metadata.name,
                status=status,
                image=pod.spec.containers[0].image,
                pod_ip=pod.status.pod_ip,
                host_ip=pod.status.host_ip,
                started_at=pod.status.start_time.isoformat() if pod.status.start_time else None,
                restart_count=container_status.restart_count if container_status else 0,
                message=pod.status.message,
            )

        except ApiException as e:
            if e.status == 404:
                return None
            logger.error(f"Failed to get pod status for {name}: {e}")
            return None

    async def list_containers(
        self,
        namespace: str = "default",
        labels: Optional[Dict[str, str]] = None
    ) -> List[ContainerInfo]:
        """List Kubernetes pods.

        Args:
            namespace: Kubernetes namespace
            labels: Filter by labels

        Returns:
            List of container information
        """
        await self._ensure_initialized()

        try:
            # Build label selector
            label_selector = None
            if labels:
                label_selector = ",".join([f"{k}={v}" for k, v in labels.items()])

            pods = await self.core_v1.list_namespaced_pod(
                namespace=namespace,
                label_selector=label_selector
            )

            containers = []
            for pod in pods.items:
                status = self._convert_status(pod.status.phase)
                container_status = pod.status.container_statuses[0] if pod.status.container_statuses else None

                containers.append(ContainerInfo(
                    name=pod.metadata.name,
                    status=status,
                    image=pod.spec.containers[0].image,
                    pod_ip=pod.status.pod_ip,
                    host_ip=pod.status.host_ip,
                    started_at=pod.status.start_time.isoformat() if pod.status.start_time else None,
                    restart_count=container_status.restart_count if container_status else 0,
                    message=pod.status.message,
                ))

            return containers

        except ApiException as e:
            logger.error(f"Failed to list pods in namespace {namespace}: {e}")
            return []

    async def get_container_logs(
        self,
        name: str,
        namespace: str = "default",
        tail_lines: int = 100,
        follow: bool = False
    ) -> str:
        """Get Kubernetes pod logs.

        Args:
            name: Pod name
            namespace: Kubernetes namespace
            tail_lines: Number of lines to return from end
            follow: Stream logs in real-time (not implemented)

        Returns:
            Log output
        """
        await self._ensure_initialized()

        try:
            logs = await self.core_v1.read_namespaced_pod_log(
                name=name,
                namespace=namespace,
                tail_lines=tail_lines
            )
            return logs

        except ApiException as e:
            logger.error(f"Failed to get logs for pod {name}: {e}")
            return f"Error retrieving logs: {e}"

    async def restart_container(
        self,
        name: str,
        namespace: str = "default"
    ) -> bool:
        """Restart a Kubernetes pod by deleting it.

        Note: This assumes the pod is managed by a higher-level controller
        (Deployment, StatefulSet, etc.) that will recreate it. For standalone
        pods, you need to manually recreate them.

        Args:
            name: Pod name
            namespace: Kubernetes namespace

        Returns:
            True if successful
        """
        await self._ensure_initialized()

        try:
            # Get pod configuration before deletion
            pod = await self.core_v1.read_namespaced_pod(
                name=name,
                namespace=namespace
            )

            # Delete the pod
            await self.delete_container(name, namespace)

            # If pod has no owner (standalone pod), we should recreate it
            if not pod.metadata.owner_references:
                logger.warning(
                    f"Pod {name} is a standalone pod without owner. "
                    "Manual recreation may be required."
                )

            return True

        except ApiException as e:
            logger.error(f"Failed to restart pod {name}: {e}")
            return False

    async def exec_command(
        self,
        name: str,
        command: List[str],
        namespace: str = "default"
    ) -> tuple[str, str]:
        """Execute command in Kubernetes pod.

        Args:
            name: Pod name
            command: Command to execute
            namespace: Kubernetes namespace

        Returns:
            Tuple of (stdout, stderr)
        """
        await self._ensure_initialized()

        try:
            # Use websocket client for exec
            ws_client = WsApiClient()
            exec_api = client.CoreV1Api(ws_client)

            resp = await exec_api.connect_get_namespaced_pod_exec(
                name=name,
                namespace=namespace,
                command=command,
                stderr=True,
                stdin=False,
                stdout=True,
                tty=False
            )

            await ws_client.close()
            return resp, ""

        except ApiException as e:
            logger.error(f"Failed to execute command in pod {name}: {e}")
            return "", str(e)

    async def health_check(self) -> bool:
        """Check if Kubernetes API is available and healthy.

        Returns:
            True if healthy
        """
        try:
            await self._ensure_initialized()
            # Try to list namespaces as a health check
            await self.core_v1.list_namespace(limit=1)
            return True

        except Exception as e:
            logger.error(f"Kubernetes health check failed: {e}")
            return False

    async def close(self):
        """Close Kubernetes client."""
        if self.api_client:
            await self.api_client.close()
            self._initialized = False

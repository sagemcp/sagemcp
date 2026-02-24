"""Docker orchestrator implementation for local development."""

import logging
from typing import Dict, List, Optional

import aiodocker
from aiodocker.exceptions import DockerError

from .base import BaseOrchestrator, ContainerConfig, ContainerInfo, ContainerStatus

logger = logging.getLogger(__name__)


class DockerOrchestrator(BaseOrchestrator):
    """Docker-based orchestrator for local development."""

    def __init__(self):
        """Initialize Docker orchestrator."""
        self.docker: Optional[aiodocker.Docker] = None
        self._initialized = False

    async def _ensure_initialized(self):
        """Ensure Docker client is initialized."""
        if self._initialized:
            return

        try:
            self.docker = aiodocker.Docker()
            # Test connection
            await self.docker.version()
            self._initialized = True
            logger.info("Docker client initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            raise

    def _convert_status(self, state: dict) -> ContainerStatus:
        """Convert Docker container state to ContainerStatus.

        Args:
            state: Docker container state dict

        Returns:
            ContainerStatus enum value
        """
        status = state.get("Status", "").lower()

        if status == "running":
            return ContainerStatus.RUNNING
        elif status in ["created", "restarting"]:
            return ContainerStatus.PENDING
        elif status == "exited":
            exit_code = state.get("ExitCode", 0)
            return ContainerStatus.SUCCEEDED if exit_code == 0 else ContainerStatus.FAILED
        elif status == "dead":
            return ContainerStatus.FAILED
        else:
            return ContainerStatus.UNKNOWN

    async def create_container(
        self,
        config: ContainerConfig,
        namespace: str = "default"
    ) -> str:
        """Create a new Docker container.

        Args:
            config: Container configuration
            namespace: Docker network name (equivalent to K8s namespace)

        Returns:
            Container ID
        """
        await self._ensure_initialized()

        # Build container configuration
        container_config = {
            "Image": config.image,
            "Hostname": config.name,
            "Env": [f"{key}={value}" for key, value in config.env.items()],
            "Labels": {
                **config.labels,
                "sage-mcp.namespace": namespace,
                "sage-mcp.container-name": config.name,
            },
            "HostConfig": {
                "RestartPolicy": {"Name": config.restart_policy.lower()},
                "NetworkMode": namespace if namespace != "default" else "bridge",
            }
        }

        # Add command if specified
        if config.command:
            container_config["Cmd"] = config.command + (config.args or [])

        # Add port bindings
        if config.ports:
            container_config["ExposedPorts"] = {
                f"{port}/tcp": {} for port in config.ports
            }
            # For local dev, map to random host ports
            container_config["HostConfig"]["PortBindings"] = {
                f"{port}/tcp": [{"HostPort": ""}] for port in config.ports
            }

        # Add resource limits
        if config.cpu_limit or config.memory_limit:
            # Convert K8s resource format to Docker format
            memory_mb = self._parse_memory(config.memory_limit)
            nano_cpus = self._parse_cpu(config.cpu_limit)

            if memory_mb:
                container_config["HostConfig"]["Memory"] = memory_mb * 1024 * 1024
            if nano_cpus:
                container_config["HostConfig"]["NanoCpus"] = nano_cpus

        # Add volumes
        if config.volumes:
            binds = []
            volumes = {}
            for vol_name, mount_path in config.volumes.items():
                # Create named volumes
                volume_name = f"{config.name}-{vol_name}"
                binds.append(f"{volume_name}:{mount_path}")
                volumes[mount_path] = {}

            container_config["Volumes"] = volumes
            container_config["HostConfig"]["Binds"] = binds

        try:
            # Pull image if not available locally
            logger.info(f"Pulling image {config.image}...")
            try:
                await self.docker.images.pull(config.image)
                logger.info(f"Successfully pulled image {config.image}")
            except Exception as e:
                logger.warning(f"Failed to pull image {config.image}: {e}")
                # Continue anyway - image might already exist locally

            # Ensure network exists
            await self._ensure_network(namespace)

            # Create container
            container = await self.docker.containers.create(
                config=container_config,
                name=config.name
            )

            # Start container
            await container.start()

            logger.info(f"Created and started Docker container {config.name}")
            return container.id

        except DockerError as e:
            logger.error(f"Failed to create Docker container {config.name}: {e}")
            raise

    async def delete_container(
        self,
        name: str,
        namespace: str = "default"
    ) -> bool:
        """Delete a Docker container.

        Args:
            name: Container name
            namespace: Docker network name

        Returns:
            True if successful
        """
        await self._ensure_initialized()

        try:
            container = await self.docker.containers.get(name)
            await container.stop()
            await container.delete()
            logger.info(f"Deleted Docker container {name}")
            return True

        except DockerError as e:
            if e.status == 404:
                logger.warning(f"Container {name} not found")
                return True
            logger.error(f"Failed to delete Docker container {name}: {e}")
            return False

    async def get_container_status(
        self,
        name: str,
        namespace: str = "default"
    ) -> Optional[ContainerInfo]:
        """Get Docker container status.

        Args:
            name: Container name
            namespace: Docker network name

        Returns:
            Container information or None if not found
        """
        await self._ensure_initialized()

        try:
            container = await self.docker.containers.get(name)
            info = await container.show()

            state = info["State"]
            config = info["Config"]
            network_settings = info["NetworkSettings"]

            status = self._convert_status(state)

            return ContainerInfo(
                name=info["Name"].lstrip("/"),
                status=status,
                image=config["Image"],
                pod_ip=network_settings.get("IPAddress"),
                host_ip="127.0.0.1",
                started_at=state.get("StartedAt"),
                restart_count=state.get("RestartCount", 0),
                message=state.get("Error") or None,
            )

        except DockerError as e:
            if e.status == 404:
                return None
            logger.error(f"Failed to get Docker container status for {name}: {e}")
            return None

    async def list_containers(
        self,
        namespace: str = "default",
        labels: Optional[Dict[str, str]] = None
    ) -> List[ContainerInfo]:
        """List Docker containers.

        Args:
            namespace: Docker network name
            labels: Filter by labels

        Returns:
            List of container information
        """
        await self._ensure_initialized()

        try:
            # Build label filter
            filters = {"label": [f"sage-mcp.namespace={namespace}"]}
            if labels:
                for key, value in labels.items():
                    filters["label"].append(f"{key}={value}")

            containers = await self.docker.containers.list(
                all=True,
                filters=filters
            )

            container_infos = []
            for container in containers:
                info = await container.show()
                state = info["State"]
                config = info["Config"]
                network_settings = info["NetworkSettings"]

                status = self._convert_status(state)

                container_infos.append(ContainerInfo(
                    name=info["Name"].lstrip("/"),
                    status=status,
                    image=config["Image"],
                    pod_ip=network_settings.get("IPAddress"),
                    host_ip="127.0.0.1",
                    started_at=state.get("StartedAt"),
                    restart_count=state.get("RestartCount", 0),
                    message=state.get("Error") or None,
                ))

            return container_infos

        except DockerError as e:
            logger.error(f"Failed to list Docker containers: {e}")
            return []

    async def get_container_logs(
        self,
        name: str,
        namespace: str = "default",
        tail_lines: int = 100,
        follow: bool = False
    ) -> str:
        """Get Docker container logs.

        Args:
            name: Container name
            namespace: Docker network name
            tail_lines: Number of lines to return from end
            follow: Stream logs in real-time (not implemented)

        Returns:
            Log output
        """
        await self._ensure_initialized()

        try:
            container = await self.docker.containers.get(name)
            logs = await container.log(
                stdout=True,
                stderr=True,
                tail=tail_lines
            )
            return "".join(logs)

        except DockerError as e:
            logger.error(f"Failed to get Docker container logs for {name}: {e}")
            return f"Error retrieving logs: {e}"

    async def restart_container(
        self,
        name: str,
        namespace: str = "default"
    ) -> bool:
        """Restart a Docker container.

        Args:
            name: Container name
            namespace: Docker network name

        Returns:
            True if successful
        """
        await self._ensure_initialized()

        try:
            container = await self.docker.containers.get(name)
            await container.restart()
            logger.info(f"Restarted Docker container {name}")
            return True

        except DockerError as e:
            logger.error(f"Failed to restart Docker container {name}: {e}")
            return False

    async def exec_command(
        self,
        name: str,
        command: List[str],
        namespace: str = "default"
    ) -> tuple[str, str]:
        """Execute command in Docker container.

        Args:
            name: Container name
            command: Command to execute
            namespace: Docker network name

        Returns:
            Tuple of (stdout, stderr)
        """
        await self._ensure_initialized()

        try:
            container = await self.docker.containers.get(name)
            exec_instance = await container.exec(
                cmd=command,
                stdout=True,
                stderr=True
            )

            output = await exec_instance.start()
            stdout = output.get("stdout", b"").decode("utf-8")
            stderr = output.get("stderr", b"").decode("utf-8")

            return stdout, stderr

        except DockerError as e:
            logger.error(f"Failed to execute command in Docker container {name}: {e}")
            return "", str(e)

    async def health_check(self) -> bool:
        """Check if Docker daemon is available and healthy.

        Returns:
            True if healthy
        """
        try:
            await self._ensure_initialized()
            await self.docker.version()
            return True

        except Exception as e:
            logger.error(f"Docker health check failed: {e}")
            return False

    async def _ensure_network(self, network_name: str):
        """Ensure Docker network exists.

        Args:
            network_name: Network name
        """
        if network_name == "default":
            return  # Use default bridge network

        try:
            await self.docker.networks.get(network_name)
        except DockerError as e:
            if e.status == 404:
                # Create network if it doesn't exist
                await self.docker.networks.create(
                    config={
                        "Name": network_name,
                        "Driver": "bridge",
                        "Labels": {"sage-mcp.namespace": network_name}
                    }
                )
                logger.info(f"Created Docker network {network_name}")
            else:
                raise

    def _parse_memory(self, memory_str: str) -> Optional[int]:
        """Parse Kubernetes memory format to megabytes.

        Args:
            memory_str: Memory string (e.g., "512Mi", "1Gi")

        Returns:
            Memory in megabytes
        """
        if not memory_str:
            return None

        memory_str = memory_str.strip()
        if memory_str.endswith("Mi"):
            return int(memory_str[:-2])
        elif memory_str.endswith("Gi"):
            return int(memory_str[:-2]) * 1024
        elif memory_str.endswith("M"):
            return int(memory_str[:-1])
        elif memory_str.endswith("G"):
            return int(memory_str[:-1]) * 1024
        else:
            # Assume bytes, convert to MB
            return int(memory_str) // (1024 * 1024)

    def _parse_cpu(self, cpu_str: str) -> Optional[int]:
        """Parse Kubernetes CPU format to Docker NanoCPUs.

        Args:
            cpu_str: CPU string (e.g., "500m", "2")

        Returns:
            CPU in NanoCPUs (1 CPU = 1e9 NanoCPUs)
        """
        if not cpu_str:
            return None

        cpu_str = cpu_str.strip()
        if cpu_str.endswith("m"):
            # Millicores to NanoCPUs
            millicores = int(cpu_str[:-1])
            return int((millicores / 1000) * 1e9)
        else:
            # Cores to NanoCPUs
            cores = float(cpu_str)
            return int(cores * 1e9)

    async def close(self):
        """Close Docker client."""
        if self.docker:
            await self.docker.close()
            self._initialized = False

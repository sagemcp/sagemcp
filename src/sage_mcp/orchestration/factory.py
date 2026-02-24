"""Orchestrator factory with auto-detection."""

import logging
import os
from typing import Optional

from .base import BaseOrchestrator
from .docker import DockerOrchestrator
from .kubernetes import KubernetesOrchestrator

logger = logging.getLogger(__name__)


class OrchestratorFactory:
    """Factory for creating orchestrator instances with auto-detection."""

    _instance: Optional[BaseOrchestrator] = None
    _orchestrator_type: Optional[str] = None

    @classmethod
    def detect_environment(cls) -> str:
        """Auto-detect the orchestration environment.

        Detection logic:
        1. Check ORCHESTRATOR environment variable (manual override)
        2. Check if running in Kubernetes (KUBERNETES_SERVICE_HOST)
        3. Check if Docker is available
        4. Fall back to Kubernetes (will fail gracefully if not available)

        Returns:
            "kubernetes" or "docker"
        """
        # Manual override
        orchestrator = os.getenv("ORCHESTRATOR", "").lower()
        if orchestrator in ["kubernetes", "k8s"]:
            logger.info("Orchestrator manually set to Kubernetes via ORCHESTRATOR env")
            return "kubernetes"
        elif orchestrator == "docker":
            logger.info("Orchestrator manually set to Docker via ORCHESTRATOR env")
            return "docker"

        # Check if running inside Kubernetes
        if os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount"):
            logger.info("Detected Kubernetes environment (serviceaccount found)")
            return "kubernetes"

        # Check for Kubernetes service host
        if os.getenv("KUBERNETES_SERVICE_HOST"):
            logger.info("Detected Kubernetes environment (KUBERNETES_SERVICE_HOST)")
            return "kubernetes"

        # Check if we're in Docker Compose (common in development)
        if os.path.exists("/.dockerenv") or os.getenv("DOCKER_COMPOSE"):
            logger.info("Detected Docker environment")
            return "docker"

        # Default to Kubernetes for production
        logger.info("Defaulting to Kubernetes orchestrator")
        return "kubernetes"

    @classmethod
    def create(cls, orchestrator_type: Optional[str] = None) -> BaseOrchestrator:
        """Create orchestrator instance.

        Args:
            orchestrator_type: Type of orchestrator ("kubernetes" or "docker").
                              If None, auto-detect.

        Returns:
            Orchestrator instance

        Raises:
            ValueError: If orchestrator type is invalid
        """
        if orchestrator_type is None:
            orchestrator_type = cls.detect_environment()

        if orchestrator_type in ["kubernetes", "k8s"]:
            logger.info("Creating Kubernetes orchestrator")
            return KubernetesOrchestrator()
        elif orchestrator_type == "docker":
            logger.info("Creating Docker orchestrator")
            return DockerOrchestrator()
        else:
            raise ValueError(
                f"Invalid orchestrator type: {orchestrator_type}. "
                f"Must be 'kubernetes' or 'docker'"
            )

    @classmethod
    def get_instance(cls, orchestrator_type: Optional[str] = None) -> BaseOrchestrator:
        """Get singleton orchestrator instance.

        Args:
            orchestrator_type: Type of orchestrator. If None, auto-detect.

        Returns:
            Orchestrator instance
        """
        if orchestrator_type is None:
            orchestrator_type = cls.detect_environment()

        # Return existing instance if type matches
        if cls._instance and cls._orchestrator_type == orchestrator_type:
            return cls._instance

        # Create new instance
        cls._instance = cls.create(orchestrator_type)
        cls._orchestrator_type = orchestrator_type

        return cls._instance

    @classmethod
    def reset(cls):
        """Reset singleton instance (useful for testing)."""
        cls._instance = None
        cls._orchestrator_type = None


# Global convenience function
def get_orchestrator(orchestrator_type: Optional[str] = None) -> BaseOrchestrator:
    """Get orchestrator instance.

    Args:
        orchestrator_type: Type of orchestrator. If None, auto-detect.

    Returns:
        Orchestrator instance
    """
    return OrchestratorFactory.get_instance(orchestrator_type)

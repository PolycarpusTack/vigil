"""Base storage backend interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict

from vigil.core.event import AuditEvent


class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize storage backend.

        Args:
            config: Backend configuration
        """
        self.config = config
        self.enabled = config.get("enabled", True)

    @abstractmethod
    def store(self, event: AuditEvent):
        """
        Store an audit event.

        Args:
            event: AuditEvent to store

        Raises:
            StorageError: If storage fails
        """
        pass

    def close(self):
        """Close/cleanup the storage backend."""
        pass

    def __repr__(self) -> str:
        """String representation."""
        return f"{self.__class__.__name__}(enabled={self.enabled})"

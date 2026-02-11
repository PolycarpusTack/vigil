"""Core Vigil components."""

from vigil.core.context import AuditContext
from vigil.core.decorators import audit_log
from vigil.core.engine import AuditEngine
from vigil.core.event import AuditEvent
from vigil.core.exceptions import (
    AuditFrameworkError,
    ConfigurationError,
    ProcessingError,
    StorageError,
)

__all__ = [
    "AuditEngine",
    "AuditEvent",
    "AuditContext",
    "audit_log",
    "AuditFrameworkError",
    "ConfigurationError",
    "StorageError",
    "ProcessingError",
]

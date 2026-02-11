"""
Vigil - A framework-agnostic, production-ready audit logging system.

Simple usage:
    from vigil import audit_log

    @audit_log
    def my_function():
        pass

Advanced usage:
    from vigil import AuditEngine, AuditContext

    audit = AuditEngine(config_file="audit.yaml")

    with AuditContext(action="OPERATION"):
        do_something()
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__license__ = "MIT"

# Standard library imports
import threading
from typing import Optional

from vigil.core.context import AuditContext
from vigil.core.decorators import audit_log

# Core exports
from vigil.core.engine import AuditEngine
from vigil.core.enums import ActionCategory, ActionType
from vigil.core.event import AuditEvent
from vigil.core.exceptions import (
    AuditFrameworkError,
    ConfigurationError,
    ProcessingError,
    StorageError,
)

# Convenience exports
from vigil.utils.config import AuditConfig

__all__ = [
    # Core
    "AuditEngine",
    "AuditEvent",
    "AuditContext",
    "audit_log",
    # Enums
    "ActionCategory",
    "ActionType",
    # Configuration
    "AuditConfig",
    # Exceptions
    "AuditFrameworkError",
    "ConfigurationError",
    "StorageError",
    "ProcessingError",
    # Metadata
    "__version__",
]


def get_version() -> str:
    """Return the version string."""
    return __version__


# Create a default global instance for convenience
_default_engine = None
_engine_lock = threading.Lock()


def get_default_engine() -> AuditEngine:
    """Get or create the default global audit engine.

    Thread-safe singleton implementation using double-checked locking.

    Returns:
        AuditEngine: The default global audit engine instance.
    """
    global _default_engine
    if _default_engine is None:
        with _engine_lock:
            # Double-check pattern: verify again inside lock
            if _default_engine is None:
                _default_engine = AuditEngine()
    return _default_engine


def configure(config_file: Optional[str] = None, **kwargs):
    """Configure the default global audit engine.

    Thread-safe configuration of the global engine instance.

    Args:
        config_file: Path to configuration file.
        **kwargs: Additional configuration overrides.
    """
    global _default_engine
    with _engine_lock:
        _default_engine = AuditEngine(config_file=config_file, **kwargs)


# Convenience functions using the default engine
def log(action: str, **kwargs):
    """Log an audit event using the default engine."""
    return get_default_engine().log(action=action, **kwargs)


def log_event(event: dict):
    """Log a complete audit event using the default engine."""
    return get_default_engine().log_event(event)

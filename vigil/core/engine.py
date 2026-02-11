"""Core audit engine."""

import logging
import platform
import sys
from typing import Any, Dict, List, Optional

from vigil.core.enums import validate_action_type, validate_category
from vigil.core.event import (
    ActionContext,
    ActorContext,
    AuditEvent,
    ErrorInfo,
    PerformanceMetrics,
)
from vigil.core.exceptions import ProcessingError, StorageError
from vigil.utils.config import AuditConfig

logger = logging.getLogger(__name__)


class AuditEngine:
    """Main audit logging engine."""

    def __init__(
        self,
        config_file: Optional[str] = None,
        config: Optional[AuditConfig] = None,
        config_dict: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """
        Initialize audit engine.

        Args:
            config_file: Path to configuration file
            config: AuditConfig instance (overrides config_file)
            config_dict: Configuration dictionary
            **kwargs: Additional configuration overrides
        """
        # Load configuration
        if config:
            self.config = config
        elif config_dict:
            self.config = AuditConfig(config_file=config_file, config_dict=config_dict)
            # Apply any additional kwargs as overrides
            if kwargs:
                self.config.merge_config(kwargs)
        elif config_file or kwargs:
            self.config = AuditConfig(config_file=config_file, config_dict=kwargs)
        else:
            # Use default configuration
            self.config = AuditConfig()

        # Initialize storage backends
        self.storage_backends: List[Any] = []
        self._init_storage_backends()

        # Initialize processing pipeline
        self.sanitizer: Optional[Any] = None
        if self.config.sanitization_enabled:
            self._init_sanitizer()

        # System information (cached)
        self._system_info = self._get_system_info()

        # Statistics
        self._stats = {"events_logged": 0, "errors": 0}

        logger.info(
            f"AuditEngine initialized: app={self.config.application_name}, "
            f"enabled={self.config.enabled}, backends={len(self.storage_backends)}"
        )

    def _init_storage_backends(self):
        """Initialize configured storage backends."""
        from vigil.storage.file_storage import FileStorageBackend

        backends_config = self.config.storage_backends

        for backend_config in backends_config:
            if not backend_config.get("enabled", True):
                continue

            backend_type = backend_config.get("type", "file")

            try:
                if backend_type == "file":
                    backend = FileStorageBackend(backend_config)
                    self.storage_backends.append(backend)
                    logger.info(
                        f"Initialized file storage backend: " f"{backend_config.get('directory')}"
                    )
                elif backend_type == "sql":
                    from vigil.storage.sql_storage import SQLStorageBackend

                    backend = SQLStorageBackend(backend_config)
                    self.storage_backends.append(backend)
                    logger.info(f"Initialized SQL storage backend: " f"{backend_config.get('url')}")
                else:
                    logger.warning(f"Unknown storage backend type: {backend_type}")
            except Exception as e:
                logger.error(f"Failed to initialize {backend_type} backend: {e}")

        if not self.storage_backends:
            logger.warning("No storage backends initialized, using default file storage")
            # Fallback to default file storage
            default_backend = FileStorageBackend({"directory": "./logs/audit", "format": "json"})
            self.storage_backends.append(default_backend)

    def _init_sanitizer(self):
        """Initialize PII sanitizer."""
        try:
            from vigil.processing.sanitizers import PIISanitizer

            self.sanitizer = PIISanitizer()
            logger.info("PII sanitizer initialized")
        except ImportError:
            logger.warning("PIISanitizer not available, sanitization disabled")

    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information (cached)."""
        return {
            "host": {
                "hostname": platform.node(),
                "os": platform.system(),
                "os_version": platform.release(),
                "architecture": platform.machine(),
            },
            "runtime": {
                "python_version": sys.version.split()[0],
                "platform": sys.platform,
            },
        }

    def log(
        self,
        action: str,
        category: str = "SYSTEM",
        action_type: str = "EXECUTE",
        actor: Optional[Dict[str, Any]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None,
        performance: Optional[Dict[str, Any]] = None,
        error: Optional[Dict[str, Any]] = None,
        custom: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Optional[AuditEvent]:
        """
        Log an audit event.

        Args:
            action: Action operation (e.g., "query_execution", "user_login")
            category: Action category (DATABASE, API, AUTH, SYSTEM, etc.)
            action_type: Action type (READ, WRITE, EXECUTE, LOGIN, etc.)
            actor: Actor context (user, system)
            parameters: Action parameters
            result: Action result
            performance: Performance metrics
            error: Error information
            custom: Custom fields
            **kwargs: Additional fields

        Returns:
            AuditEvent instance or None if logging is disabled/failed

        Raises:
            ValueError: If action, category, or action_type are invalid
        """
        if not self.config.enabled:
            return None

        # Validate inputs
        if not action or not isinstance(action, str):
            raise ValueError("action must be a non-empty string")

        action = action.strip()
        if not action:
            raise ValueError("action cannot be empty or whitespace-only")

        # Validate and normalize category and action_type
        try:
            category = validate_category(category)
            action_type = validate_action_type(action_type)
        except ValueError as e:
            logger.error(f"Input validation failed: {e}")
            raise

        try:
            # Build event
            event = self._build_event(
                action=action,
                category=category,
                action_type=action_type,
                actor=actor,
                parameters=parameters,
                result=result,
                performance=performance,
                error=error,
                custom=custom,
                **kwargs,
            )

            # Process event (sanitization, filtering)
            event = self._process_event(event)

            # Event was filtered out
            if event is None:
                return None

            # Store event
            self._store_event(event)

            # Update statistics
            self._stats["events_logged"] += 1

            return event

        except (ProcessingError, StorageError):
            # Critical errors must propagate: PII leak prevention and total storage failure
            self._stats["errors"] += 1
            raise
        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"Failed to log audit event: {e}", exc_info=True)
            return None

    def log_event(self, event_dict: Dict[str, Any]) -> Optional[AuditEvent]:
        """
        Log a complete audit event from dictionary.

        Args:
            event_dict: Complete event dictionary

        Returns:
            AuditEvent instance or None if logging failed
        """
        if not self.config.enabled:
            return None

        try:
            event = AuditEvent.from_dict(event_dict)
            event = self._process_event(event)
            if event is None:
                return None
            self._store_event(event)
            self._stats["events_logged"] += 1
            return event
        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"Failed to log audit event: {e}", exc_info=True)
            return None

    def _build_event(
        self,
        action: str,
        category: str,
        action_type: str,
        actor: Optional[Dict] = None,
        parameters: Optional[Dict] = None,
        result: Optional[Dict] = None,
        performance: Optional[Dict] = None,
        error: Optional[Dict] = None,
        custom: Optional[Dict] = None,
        **kwargs,
    ) -> AuditEvent:
        """Build audit event from parameters."""
        # Create event
        event = AuditEvent()

        # Action context
        event.action = ActionContext(
            type=action_type,
            category=category,
            operation=action,
            parameters=parameters or {},
        )

        if result:
            event.action.result.status = result.get("status", "SUCCESS")
            event.action.result.message = result.get("message")
            event.action.result.rows_affected = result.get("rows_affected")

        # Actor context
        if actor:
            event.actor = ActorContext(**actor)

        # Performance metrics
        if performance:
            event.performance = PerformanceMetrics(**performance)

        # Error information
        if error:
            event.error = ErrorInfo(**error)

        # System info
        event.system = self._system_info.copy()

        # Custom fields
        if custom:
            event.custom = custom

        # Additional metadata
        event.metadata = kwargs.get("metadata", {})
        event.metadata["application"] = self.config.application_name
        event.metadata["environment"] = self.config.environment

        return event

    def _process_event(self, event: AuditEvent) -> Optional[AuditEvent]:
        """Process event through pipeline (sanitization, filtering).

        Args:
            event: AuditEvent to process

        Returns:
            Processed AuditEvent, or None if the event was filtered out.

        Raises:
            ProcessingError: If sanitization fails and fail_on_sanitization_error is True
        """
        # Sanitize PII if enabled
        if self.sanitizer:
            try:
                event = self.sanitizer.sanitize_event(event)
            except Exception as e:
                # Security-first approach: fail if sanitization fails
                # This prevents potential PII leaks if sanitizer is broken
                from vigil.core.exceptions import ProcessingError

                logger.error(f"Failed to sanitize event {event.event_id}: {e}", exc_info=True)

                # Check configuration for fail-safe behavior
                fail_on_error = self.config.get("vigil.fail_on_sanitization_error", True)

                if fail_on_error:
                    raise ProcessingError(
                        f"Sanitization failed for event {event.event_id}: {e}. "
                        "Event will not be logged to prevent PII leakage. "
                        "Set fail_on_sanitization_error=False to log unsanitized events."
                    )
                else:
                    logger.warning(
                        f"Logging unsanitized event {event.event_id} "
                        "(fail_on_sanitization_error=False). PII may be present!"
                    )

        # Apply filters
        if self._is_filtered(event):
            logger.debug(f"Event {event.event_id} filtered out by configured filters")
            return None

        return event

    def _is_filtered(self, event: AuditEvent) -> bool:
        """Check if an event should be filtered out based on configured filters.

        Args:
            event: AuditEvent to check

        Returns:
            True if the event should be dropped, False if it should pass through.
        """
        filters = self.config.get("vigil.processing.filters", [])
        if not filters:
            return False

        for f in filters:
            filter_type = f.get("type", "")
            if filter_type == "exclude_category":
                excluded = {c.upper() for c in f.get("categories", [])}
                if event.action.category in excluded:
                    return True
            elif filter_type == "exclude_action_type":
                excluded = {t.upper() for t in f.get("action_types", [])}
                if event.action.type in excluded:
                    return True

        return False

    def _store_event(self, event: AuditEvent):
        """Store event to all configured backends."""
        errors = []

        for backend in self.storage_backends:
            try:
                backend.store(event)
            except Exception as e:
                errors.append(f"{backend.__class__.__name__}: {e}")
                logger.error(f"Failed to store event in {backend.__class__.__name__}: {e}")

        if errors and len(errors) == len(self.storage_backends):
            # All backends failed
            raise StorageError(f"All storage backends failed: {'; '.join(errors)}")

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "events_logged": self._stats["events_logged"],
            "errors": self._stats["errors"],
            "backends": len(self.storage_backends),
            "enabled": self.config.enabled,
        }

    def shutdown(self):
        """Shutdown audit engine and flush all backends."""
        logger.info("Shutting down audit engine...")

        for backend in self.storage_backends:
            try:
                if hasattr(backend, "close"):
                    backend.close()
            except Exception as e:
                logger.error(f"Error closing backend {backend.__class__.__name__}: {e}")

        logger.info("Audit engine shutdown complete")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"AuditEngine(enabled={self.config.enabled}, "
            f"backends={len(self.storage_backends)}, "
            f"events={self._stats['events_logged']})"
        )

"""Audit context manager for automatic event capture."""

import time
import traceback
from typing import Any, Dict, Optional

from vigil.core.engine import AuditEngine


class AuditContext:
    """Context manager for automatic audit event capture."""

    def __init__(
        self,
        action: str,
        category: str = "SYSTEM",
        action_type: str = "EXECUTE",
        resource_type: Optional[str] = None,
        resource_name: Optional[str] = None,
        actor: Optional[Dict[str, Any]] = None,
        capture_exceptions: bool = True,
        engine: Optional[AuditEngine] = None,
        **kwargs,
    ):
        """
        Initialize audit context.

        Args:
            action: Action operation name
            category: Action category (DATABASE, API, etc.)
            action_type: Action type (READ, WRITE, etc.)
            resource_type: Resource type (table, file, endpoint)
            resource_name: Resource name/identifier
            actor: Actor context (user information)
            capture_exceptions: Whether to capture exceptions
            engine: AuditEngine instance (uses default if None)
            **kwargs: Additional event fields
        """
        self.action = action
        self.category = category
        self.action_type = action_type
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.actor = actor
        self.capture_exceptions = capture_exceptions
        self.kwargs = kwargs

        # Get or create engine
        if engine:
            self.engine = engine
        else:
            from vigil import get_default_engine

            self.engine = get_default_engine()

        # Timing
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.duration_ms: Optional[float] = None

        # Result tracking
        self.result_status = "SUCCESS"
        self.result_message: Optional[str] = None
        self.exception: Optional[Exception] = None

        # Custom metadata
        self.metadata: Dict[str, Any] = {}

    def __enter__(self):
        """Enter context - start timing."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - log event."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000

        # Handle exceptions
        if exc_type is not None:
            self.result_status = "FAILURE"
            self.exception = exc_val
            if exc_val:
                self.result_message = str(exc_val)

        # Log the event
        self._log_event()

        # Don't suppress exceptions
        return False

    def _log_event(self):
        """Log the audit event."""
        # Build performance metrics
        performance = {
            "duration_ms": self.duration_ms,
        }

        # Build result
        result = {
            "status": self.result_status,
            "message": self.result_message,
        }

        # Build error info
        error = None
        if self.exception and self.capture_exceptions:
            error = {
                "occurred": True,
                "type": type(self.exception).__name__,
                "message": str(self.exception),
                "stack_trace": "".join(
                    traceback.format_exception(
                        type(self.exception), self.exception, self.exception.__traceback__
                    )
                ),
                "handled": False,  # Exception is being raised
            }

        # Build resource info
        resource = {}
        if self.resource_type:
            resource["type"] = self.resource_type
        if self.resource_name:
            resource["name"] = self.resource_name

        # Log event
        self.engine.log(
            action=self.action,
            category=self.category,
            action_type=self.action_type,
            actor=self.actor,
            result=result,
            performance=performance,
            error=error,
            custom={"resource": resource, **self.metadata},
            **self.kwargs,
        )

    def add_metadata(self, key: str, value: Any):
        """
        Add custom metadata to the event.

        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value

    def success(self, message: Optional[str] = None):
        """Mark operation as successful."""
        self.result_status = "SUCCESS"
        if message:
            self.result_message = message

    def failure(self, message: Optional[str] = None, exception: Optional[Exception] = None):
        """Mark operation as failed."""
        self.result_status = "FAILURE"
        if message:
            self.result_message = message
        if exception:
            self.exception = exception

    def __repr__(self) -> str:
        """String representation."""
        return f"AuditContext(action={self.action}, category={self.category})"

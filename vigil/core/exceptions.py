"""Custom exceptions for the Vigil."""


class AuditFrameworkError(Exception):
    """Base exception for all Vigil errors."""

    pass


class ConfigurationError(AuditFrameworkError):
    """Raised when there's a configuration error."""

    pass


class StorageError(AuditFrameworkError):
    """Raised when there's a storage backend error."""

    pass


class ProcessingError(AuditFrameworkError):
    """Raised when there's an event processing error."""

    pass


class ValidationError(AuditFrameworkError):
    """Raised when event validation fails."""

    pass


class IntegrationError(AuditFrameworkError):
    """Raised when there's a framework integration error."""

    pass


class ComplianceError(AuditFrameworkError):
    """Raised when there's a compliance violation."""

    pass

"""PII sanitization for audit events."""

import logging
import re
from typing import Any, Dict, List, Pattern, Tuple

from vigil.core.event import AuditEvent

logger = logging.getLogger(__name__)


class PIISanitizer:
    """Sanitizer for removing PII from audit events."""

    def __init__(self):
        """Initialize PII sanitizer with default patterns."""
        # Compile regex patterns
        self.patterns: List[Tuple[Pattern, str, str]] = [
            # Password patterns (handles key=val, key:val, and "key":"val")
            (
                re.compile(
                    r'(?i)(password|pwd|passwd)["\s]*[=:]["\s]*([^\s,}"]+)',
                    re.IGNORECASE,
                ),
                r"\1=***REDACTED***",
                "password",
            ),
            # Credit card numbers (simple pattern)
            (
                re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
                "****-****-****-XXXX",
                "credit_card",
            ),
            # Social Security Numbers
            (
                re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
                "***-**-XXXX",
                "ssn",
            ),
            # API keys (common formats — supports _, - in key values)
            (
                re.compile(r"(?i)(api[_-]?key|token|secret)\s*[=:]\s*([a-zA-Z0-9_-]{20,})"),
                r"\1=***REDACTED***",
                "api_key",
            ),
        ]

        # Email pattern (aggressive redaction for privacy)
        # Matches complete email addresses
        self.email_pattern = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")

    def sanitize_event(self, event: AuditEvent) -> AuditEvent:
        """
        Sanitize PII from audit event.

        Args:
            event: AuditEvent to sanitize

        Returns:
            Sanitized AuditEvent
        """
        try:
            # Sanitize parameters
            if event.action.parameters:
                event.action.parameters = self._sanitize_dict(event.action.parameters)

            # Sanitize custom fields
            if event.custom:
                event.custom = self._sanitize_dict(event.custom)

            # Sanitize metadata
            if event.metadata:
                event.metadata = self._sanitize_dict(event.metadata)

            # Sanitize actor email
            if event.actor.email:
                event.actor.email = self._sanitize_email(event.actor.email)

            # Sanitize error messages
            if event.error.message:
                event.error.message = self._sanitize_string(event.error.message)

            # Sanitize error stack traces to prevent leakage of sensitive data
            if event.error.stack_trace:
                event.error.stack_trace = self._sanitize_string(event.error.stack_trace)

            return event

        except Exception as e:
            logger.warning(f"Failed to sanitize event: {e}")
            return event

    def _sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively sanitize dictionary.

        Args:
            data: Dictionary to sanitize

        Returns:
            Sanitized dictionary
        """
        if not isinstance(data, dict):
            return data

        sanitized: Dict[str, Any] = {}
        for key, value in data.items():
            # Check if key suggests sensitive data
            key_lower = key.lower()
            sensitive_keys = ["password", "pwd", "secret", "token", "api_key", "credit_card", "ssn"]
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = self._sanitize_list(value)
            elif isinstance(value, str):
                sanitized[key] = self._sanitize_string(value)
            else:
                sanitized[key] = value

        return sanitized

    def _sanitize_list(self, data: List[Any]) -> List[Any]:
        """
        Recursively sanitize list.

        Args:
            data: List to sanitize

        Returns:
            Sanitized list
        """
        if not isinstance(data, list):
            return data

        sanitized: List[Any] = []
        for item in data:
            if isinstance(item, dict):
                sanitized.append(self._sanitize_dict(item))
            elif isinstance(item, list):
                sanitized.append(self._sanitize_list(item))
            elif isinstance(item, str):
                sanitized.append(self._sanitize_string(item))
            else:
                sanitized.append(item)

        return sanitized

    def _sanitize_string(self, text: str) -> str:
        """
        Sanitize string using regex patterns.

        Args:
            text: String to sanitize

        Returns:
            Sanitized string
        """
        if not isinstance(text, str):
            return text

        # Apply all patterns
        sanitized = text
        for pattern, replacement, _name in self.patterns:
            sanitized = pattern.sub(replacement, sanitized)

        # Sanitize emails (partial redaction)
        sanitized = self._sanitize_email(sanitized)

        return sanitized

    def _sanitize_email(self, text: str) -> str:
        """
        Sanitize email addresses with aggressive redaction for privacy.

        Completely redacts email addresses to prevent identification.
        Uses generic placeholder to indicate an email was present.

        Args:
            text: String potentially containing emails

        Returns:
            String with emails completely redacted
        """
        if not isinstance(text, str):
            return text

        # Completely redact email addresses for maximum privacy
        # Format: ***EMAIL_REDACTED***
        return self.email_pattern.sub("***EMAIL_REDACTED***", text)

    def add_pattern(self, pattern: str, replacement: str, name: str = "custom"):
        """
        Add custom sanitization pattern.

        Args:
            pattern: Regex pattern string
            replacement: Replacement string
            name: Pattern name

        Raises:
            ProcessingError: If pattern is invalid regex
        """
        from vigil.core.exceptions import ProcessingError

        if not pattern:
            raise ProcessingError("pattern cannot be empty")

        if not isinstance(pattern, str):
            raise ProcessingError("pattern must be a string")

        try:
            compiled_pattern = re.compile(pattern)
            self.patterns.append((compiled_pattern, replacement, name))
            logger.info(f"Added custom sanitization pattern: {name}")
        except re.error as e:
            raise ProcessingError(
                f"Invalid regex pattern '{pattern}' for sanitization rule '{name}': {e}"
            )

    def __repr__(self) -> str:
        """String representation."""
        return f"PIISanitizer(patterns={len(self.patterns)})"

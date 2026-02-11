"""Unit tests for vigil package-level convenience functions.

Tests cover:
- get_version()
- get_default_engine() singleton
- configure()
- log() convenience function
- log_event() convenience function
- storage __init__ get_sql_storage_backend()
"""

from unittest.mock import MagicMock

import vigil
from vigil.storage import get_sql_storage_backend


class TestPackageVersion:
    """Tests for version helpers."""

    def test_get_version_returns_string(self):
        """get_version returns version string."""
        version = vigil.get_version()
        assert isinstance(version, str)
        assert version == vigil.__version__


class TestDefaultEngine:
    """Tests for the default engine singleton."""

    def test_get_default_engine_returns_engine(self):
        """get_default_engine returns an AuditEngine instance."""
        # Reset the singleton
        vigil._default_engine = None
        engine = vigil.get_default_engine()
        assert isinstance(engine, vigil.AuditEngine)

    def test_get_default_engine_is_singleton(self):
        """Repeated calls return the same instance."""
        vigil._default_engine = None
        e1 = vigil.get_default_engine()
        e2 = vigil.get_default_engine()
        assert e1 is e2

    def test_configure_creates_new_engine(self):
        """configure() replaces the default engine."""
        vigil._default_engine = None
        old = vigil.get_default_engine()
        vigil.configure()
        new = vigil.get_default_engine()
        assert old is not new


class TestConvenienceFunctions:
    """Tests for log() and log_event() module-level functions."""

    def test_log_calls_engine(self):
        """log() delegates to default engine."""
        vigil._default_engine = None
        engine = MagicMock()
        vigil._default_engine = engine

        vigil.log(action="test_action", category="API")
        engine.log.assert_called_once_with(action="test_action", category="API")

        # Cleanup
        vigil._default_engine = None

    def test_log_event_calls_engine(self):
        """log_event() delegates to default engine."""
        vigil._default_engine = None
        engine = MagicMock()
        vigil._default_engine = engine

        vigil.log_event({"action": {"type": "READ"}})
        engine.log_event.assert_called_once_with({"action": {"type": "READ"}})

        # Cleanup
        vigil._default_engine = None


class TestStorageInit:
    """Tests for storage __init__ lazy import."""

    def test_get_sql_storage_backend(self):
        """get_sql_storage_backend returns the SQLStorageBackend class."""
        from vigil.storage.sql_storage import SQLStorageBackend

        cls = get_sql_storage_backend()
        assert cls is SQLStorageBackend

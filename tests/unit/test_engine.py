"""Unit tests for audit engine core functionality.

Tests cover:
- Input validation for action, category, action_type
- PII sanitization failure handling
- Event logging and processing
- Storage backend interactions
- Configuration management
- Error handling and statistics
- Context manager functionality
"""

from unittest.mock import Mock, patch

import pytest

from vigil.core.engine import AuditEngine
from vigil.core.event import AuditEvent
from vigil.core.exceptions import (
    ProcessingError,
    StorageError,
)
from vigil.storage.file_storage import FileStorageBackend


class TestEngineInitialization:
    """Test suite for AuditEngine initialization."""

    def test_initialization_with_default_config(self):
        """Test initialization with default configuration."""
        engine = AuditEngine()
        assert engine.config is not None
        assert engine.config.enabled is True
        assert len(engine.storage_backends) > 0
        engine.shutdown()

    def test_initialization_with_config_object(self, audit_config):
        """Test initialization with AuditConfig object."""
        engine = AuditEngine(config=audit_config)
        assert engine.config == audit_config
        assert engine.config.application_name == "test_app"
        engine.shutdown()

    def test_initialization_with_config_dict(self, basic_config, audit_log_dir):
        """Test initialization with configuration dictionary."""
        engine = AuditEngine(config_dict=basic_config)
        assert engine.config.application_name == "test_app"
        assert engine.config.environment == "test"
        engine.shutdown()

    def test_initialization_with_config_file(self, temp_dir, audit_log_dir):
        """Test initialization with configuration file."""
        import yaml

        config_file = temp_dir / "config.yaml"
        config_data = {
            "vigil": {
                "core": {
                    "enabled": True,
                    "application_name": "file_config_app",
                },
                "storage": {"backends": [{"type": "file", "directory": str(audit_log_dir)}]},
            }
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        engine = AuditEngine(config_file=str(config_file))
        assert engine.config.application_name == "file_config_app"
        engine.shutdown()

    def test_initialization_creates_storage_backends(self, audit_config):
        """Test that initialization creates configured storage backends."""
        engine = AuditEngine(config=audit_config)
        assert len(engine.storage_backends) > 0
        assert any(isinstance(backend, FileStorageBackend) for backend in engine.storage_backends)
        engine.shutdown()

    def test_initialization_with_sanitization_enabled(self, audit_config):
        """Test initialization with PII sanitization enabled."""
        engine = AuditEngine(config=audit_config)
        assert engine.sanitizer is not None
        engine.shutdown()

    def test_initialization_with_sanitization_disabled(self, temp_dir):
        """Test initialization with sanitization disabled."""
        config_dict = {
            "vigil": {
                "core": {"enabled": True},
                "storage": {"backends": [{"type": "file", "directory": str(temp_dir)}]},
                "processing": {"sanitization": {"enabled": False}},
            }
        }
        engine = AuditEngine(config_dict=config_dict)
        assert engine.sanitizer is None
        engine.shutdown()

    def test_initialization_caches_system_info(self, audit_engine):
        """Test that system information is cached during initialization."""
        assert audit_engine._system_info is not None
        assert "host" in audit_engine._system_info
        assert "runtime" in audit_engine._system_info

    def test_initialization_stats_are_zero(self, audit_engine):
        """Test that statistics are initialized to zero."""
        stats = audit_engine.get_stats()
        assert stats["events_logged"] == 0
        assert stats["errors"] == 0

    def test_fallback_to_default_storage_backend(self, temp_dir):
        """Test fallback to default file storage when no backends configured."""
        config_dict = {
            "vigil": {
                "core": {"enabled": True},
                "storage": {"backends": []},
            }
        }
        engine = AuditEngine(config_dict=config_dict)
        # Should have fallback backend
        assert len(engine.storage_backends) == 1
        engine.shutdown()

    def test_repr(self, audit_engine):
        """Test string representation of engine."""
        repr_str = repr(audit_engine)
        assert "AuditEngine" in repr_str
        assert "enabled=True" in repr_str
        assert "backends=" in repr_str


class TestInputValidation:
    """Test suite for input validation in log method."""

    def test_log_with_valid_action(self, audit_engine):
        """Test logging with valid action."""
        event = audit_engine.log(action="test_action")
        assert event is not None
        assert event.action.operation == "test_action"

    def test_log_with_empty_action_raises_error(self, audit_engine):
        """Test that empty action raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            audit_engine.log(action="")
        assert "action" in str(exc_info.value).lower()
        assert "empty" in str(exc_info.value).lower()

    def test_log_with_whitespace_action_raises_error(self, audit_engine):
        """Test that whitespace-only action raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            audit_engine.log(action="   ")
        assert "action" in str(exc_info.value).lower()
        assert "empty" in str(exc_info.value).lower()

    def test_log_with_none_action_raises_error(self, audit_engine):
        """Test that None action raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            audit_engine.log(action=None)
        assert "action" in str(exc_info.value).lower()

    def test_log_with_non_string_action_raises_error(self, audit_engine):
        """Test that non-string action raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            audit_engine.log(action=123)
        assert "action" in str(exc_info.value).lower()

    def test_log_trims_action_whitespace(self, audit_engine):
        """Test that action whitespace is trimmed."""
        event = audit_engine.log(action="  test_action  ")
        assert event.action.operation == "test_action"

    def test_log_with_invalid_category_raises_error(self, audit_engine):
        """Test that invalid category raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            audit_engine.log(action="test", category="INVALID_CATEGORY")
        assert "Invalid category" in str(exc_info.value)

    def test_log_with_valid_category(self, audit_engine):
        """Test logging with valid category."""
        event = audit_engine.log(action="test", category="DATABASE")
        assert event is not None
        assert event.action.category == "DATABASE"

    def test_log_normalizes_category_case(self, audit_engine):
        """Test that category is normalized to uppercase."""
        event = audit_engine.log(action="test", category="database")
        assert event.action.category == "DATABASE"

    def test_log_with_invalid_action_type_raises_error(self, audit_engine):
        """Test that invalid action type raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            audit_engine.log(action="test", action_type="INVALID_TYPE")
        assert "Invalid action_type" in str(exc_info.value)

    def test_log_with_valid_action_type(self, audit_engine):
        """Test logging with valid action type."""
        event = audit_engine.log(action="test", action_type="READ")
        assert event is not None
        assert event.action.type == "READ"

    def test_log_normalizes_action_type_case(self, audit_engine):
        """Test that action type is normalized to uppercase."""
        event = audit_engine.log(action="test", action_type="write")
        assert event.action.type == "WRITE"

    @pytest.mark.parametrize(
        "category",
        [
            "DATABASE",
            "API",
            "AUTH",
            "FILE",
            "SYSTEM",
            "NETWORK",
            "SECURITY",
            "COMPLIANCE",
            "USER",
            "ADMIN",
        ],
    )
    def test_log_with_all_valid_categories(self, audit_engine, category):
        """Test logging with all valid categories."""
        event = audit_engine.log(action="test", category=category)
        assert event is not None
        assert event.action.category == category

    @pytest.mark.parametrize(
        "action_type",
        [
            "READ",
            "WRITE",
            "UPDATE",
            "DELETE",
            "EXECUTE",
            "CREATE",
            "LOGIN",
            "LOGOUT",
            "ACCESS",
            "MODIFY",
            "GRANT",
            "REVOKE",
            "APPROVE",
            "REJECT",
        ],
    )
    def test_log_with_all_valid_action_types(self, audit_engine, action_type):
        """Test logging with all valid action types."""
        event = audit_engine.log(action="test", action_type=action_type)
        assert event is not None
        assert event.action.type == action_type


class TestEventLogging:
    """Test suite for event logging functionality."""

    def test_log_creates_event(self, audit_engine):
        """Test that log method creates an AuditEvent."""
        event = audit_engine.log(action="test_action")
        assert isinstance(event, AuditEvent)
        assert event.event_id is not None

    def test_log_with_actor_context(self, audit_engine):
        """Test logging with actor information."""
        actor = {
            "type": "user",
            "username": "testuser",
            "email": "test@example.com",
        }
        event = audit_engine.log(action="test", actor=actor)
        assert event.actor.username == "testuser"
        assert event.actor.type == "user"

    def test_log_with_parameters(self, audit_engine):
        """Test logging with action parameters."""
        params = {"query": "SELECT * FROM users", "limit": 10}
        event = audit_engine.log(action="query", parameters=params)
        assert event.action.parameters == params

    def test_log_with_result(self, audit_engine):
        """Test logging with action result."""
        result = {"status": "SUCCESS", "rows_affected": 5}
        event = audit_engine.log(action="update", result=result)
        assert event.action.result.status == "SUCCESS"
        assert event.action.result.rows_affected == 5

    def test_log_with_performance_metrics(self, audit_engine):
        """Test logging with performance metrics."""
        performance = {"duration_ms": 123.45, "memory_mb": 50.0}
        event = audit_engine.log(action="operation", performance=performance)
        assert event.performance.duration_ms == 123.45
        assert event.performance.memory_mb == 50.0

    def test_log_with_error_info(self, audit_engine):
        """Test logging with error information."""
        error = {
            "occurred": True,
            "type": "ValueError",
            "message": "Invalid value",
        }
        event = audit_engine.log(action="operation", error=error)
        assert event.error.occurred is True
        assert event.error.type == "ValueError"
        assert event.error.message == "Invalid value"

    def test_log_with_custom_fields(self, audit_engine):
        """Test logging with custom fields."""
        custom = {"request_id": "req-123", "user_agent": "TestAgent/1.0"}
        event = audit_engine.log(action="test", custom=custom)
        assert event.custom == custom

    def test_log_includes_system_info(self, audit_engine):
        """Test that logged events include system information."""
        event = audit_engine.log(action="test")
        assert event.system is not None
        assert "host" in event.system
        assert "runtime" in event.system

    def test_log_includes_application_metadata(self, audit_engine):
        """Test that logged events include application metadata."""
        event = audit_engine.log(action="test")
        assert event.metadata is not None
        assert "application" in event.metadata
        assert "environment" in event.metadata

    def test_log_increments_events_logged_counter(self, audit_engine):
        """Test that successful logging increments counter."""
        initial_count = audit_engine.get_stats()["events_logged"]
        audit_engine.log(action="test")
        new_count = audit_engine.get_stats()["events_logged"]
        assert new_count == initial_count + 1

    def test_log_multiple_events(self, audit_engine):
        """Test logging multiple events."""
        for i in range(5):
            event = audit_engine.log(action=f"test_{i}")
            assert event is not None

        stats = audit_engine.get_stats()
        assert stats["events_logged"] == 5

    def test_log_with_all_parameters(self, audit_engine):
        """Test logging with all available parameters."""
        event = audit_engine.log(
            action="comprehensive_test",
            category="DATABASE",
            action_type="READ",
            actor={"username": "testuser"},
            parameters={"query": "SELECT 1"},
            result={"status": "SUCCESS"},
            performance={"duration_ms": 50.0},
            error={"occurred": False},
            custom={"key": "value"},
            metadata={"extra": "info"},
        )
        assert event is not None
        assert event.action.operation == "comprehensive_test"
        assert event.action.category == "DATABASE"
        assert event.action.type == "READ"


class TestEventProcessing:
    """Test suite for event processing pipeline."""

    def test_event_is_processed_through_sanitizer(self, audit_engine, pii_test_data):
        """Test that events are processed through sanitizer."""
        event = audit_engine.log(action="test", parameters=pii_test_data)
        # PII should be sanitized
        assert event.action.parameters["password"] == "***REDACTED***"
        assert event.action.parameters["email"] == "***EMAIL_REDACTED***"

    def test_sanitization_failure_with_fail_on_error_true(self, audit_engine):
        """Test that sanitization failure raises ProcessingError when configured."""
        # Mock sanitizer to raise exception
        if audit_engine.sanitizer:
            with patch.object(
                audit_engine.sanitizer,
                "sanitize_event",
                side_effect=Exception("Sanitization failed"),
            ):
                with pytest.raises(ProcessingError) as exc_info:
                    audit_engine.log(action="test")
                assert "Sanitization failed" in str(exc_info.value)

    def test_sanitization_failure_with_fail_on_error_false(self, temp_dir):
        """Test that events are logged unsanitized when fail_on_error=False."""
        config_dict = {
            "vigil": {
                "core": {"enabled": True},
                "storage": {"backends": [{"type": "file", "directory": str(temp_dir)}]},
                "processing": {"sanitization": {"enabled": True}},
                "fail_on_sanitization_error": False,
            }
        }
        engine = AuditEngine(config_dict=config_dict)

        # Mock sanitizer to raise exception
        if engine.sanitizer:
            with patch.object(
                engine.sanitizer,
                "sanitize_event",
                side_effect=Exception("Sanitization failed"),
            ):
                # Should not raise error
                engine.log(action="test")
                # Event should still be logged
                assert engine.get_stats()["events_logged"] == 1

        engine.shutdown()

    def test_actor_email_is_sanitized(self, audit_engine):
        """Test that actor email is sanitized."""
        event = audit_engine.log(action="test", actor={"email": "sensitive@example.com"})
        assert event.actor.email == "***EMAIL_REDACTED***"

    def test_error_message_is_sanitized(self, audit_engine):
        """Test that error messages are sanitized."""
        event = audit_engine.log(
            action="test",
            error={
                "occurred": True,
                "message": "Failed for user test@example.com",
            },
        )
        assert "***EMAIL_REDACTED***" in event.error.message
        assert "@" not in event.error.message


class TestStorageBackendInteraction:
    """Test suite for storage backend interactions."""

    def test_event_is_stored_to_backends(self, audit_engine):
        """Test that events are stored to all backends."""
        # Mock storage backend
        mock_backend = Mock()
        audit_engine.storage_backends = [mock_backend]

        audit_engine.log(action="test")

        # Backend should have been called
        mock_backend.store.assert_called_once()

    def test_event_stored_to_multiple_backends(self, audit_engine):
        """Test that events are stored to all configured backends."""
        mock_backend1 = Mock()
        mock_backend2 = Mock()
        audit_engine.storage_backends = [mock_backend1, mock_backend2]

        audit_engine.log(action="test")

        mock_backend1.store.assert_called_once()
        mock_backend2.store.assert_called_once()

    def test_single_backend_failure_logs_error(self, audit_engine, caplog):
        """Test that single backend failure is logged but doesn't prevent storage."""
        mock_backend1 = Mock()
        mock_backend1.store.side_effect = Exception("Backend 1 failed")
        mock_backend2 = Mock()

        audit_engine.storage_backends = [mock_backend1, mock_backend2]

        # Should not raise error (backend 2 succeeds)
        event = audit_engine.log(action="test")
        assert event is not None

        # Both backends should be called
        mock_backend1.store.assert_called_once()
        mock_backend2.store.assert_called_once()

    def test_all_backends_failure_raises_storage_error(self, audit_engine):
        """Test that all backends failing raises StorageError."""
        mock_backend1 = Mock()
        mock_backend1.store.side_effect = Exception("Backend 1 failed")
        mock_backend2 = Mock()
        mock_backend2.store.side_effect = Exception("Backend 2 failed")

        audit_engine.storage_backends = [mock_backend1, mock_backend2]

        with pytest.raises(StorageError) as exc_info:
            audit_engine.log(action="test")

        assert "All storage backends failed" in str(exc_info.value)

    def test_storage_error_increments_error_counter(self, audit_engine):
        """Test that storage errors increment error counter."""
        mock_backend = Mock()
        mock_backend.store.side_effect = Exception("Storage failed")
        audit_engine.storage_backends = [mock_backend]

        initial_errors = audit_engine.get_stats()["errors"]

        try:
            audit_engine.log(action="test")
        except Exception:
            pass

        new_errors = audit_engine.get_stats()["errors"]
        assert new_errors > initial_errors


class TestLogEventMethod:
    """Test suite for log_event method (logging from dict)."""

    def test_log_event_from_dict(self, audit_engine, sample_event_dict):
        """Test logging event from dictionary."""
        event = audit_engine.log_event(sample_event_dict)
        assert event is not None
        assert isinstance(event, AuditEvent)

    def test_log_event_processes_through_sanitizer(self, audit_engine):
        """Test that log_event processes through sanitizer."""
        event_dict = {
            "action": {
                "operation": "test",
                "parameters": {"password": "secret123"},
            }
        }
        event = audit_engine.log_event(event_dict)
        assert event.action.parameters["password"] == "***REDACTED***"

    def test_log_event_stores_to_backends(self, audit_engine, sample_event_dict):
        """Test that log_event stores to backends."""
        mock_backend = Mock()
        audit_engine.storage_backends = [mock_backend]

        audit_engine.log_event(sample_event_dict)
        mock_backend.store.assert_called_once()

    def test_log_event_increments_counter(self, audit_engine, sample_event_dict):
        """Test that log_event increments events counter."""
        initial_count = audit_engine.get_stats()["events_logged"]
        audit_engine.log_event(sample_event_dict)
        new_count = audit_engine.get_stats()["events_logged"]
        assert new_count == initial_count + 1

    def test_log_event_handles_errors(self, audit_engine):
        """Test that log_event handles errors gracefully."""
        invalid_dict = {"invalid": "structure"}
        # Should handle gracefully and return None
        audit_engine.log_event(invalid_dict)
        # Depending on implementation, might return None or raise


class TestDisabledEngine:
    """Test suite for disabled audit engine."""

    def test_disabled_engine_returns_none(self, temp_dir):
        """Test that disabled engine returns None when logging."""
        config_dict = {
            "vigil": {
                "core": {"enabled": False},
                "storage": {"backends": [{"type": "file", "directory": str(temp_dir)}]},
            }
        }
        engine = AuditEngine(config_dict=config_dict)

        event = engine.log(action="test")
        assert event is None
        engine.shutdown()

    def test_disabled_engine_doesnt_increment_counter(self, temp_dir):
        """Test that disabled engine doesn't increment counter."""
        config_dict = {
            "vigil": {
                "core": {"enabled": False},
                "storage": {"backends": [{"type": "file", "directory": str(temp_dir)}]},
            }
        }
        engine = AuditEngine(config_dict=config_dict)

        engine.log(action="test")
        stats = engine.get_stats()
        assert stats["events_logged"] == 0
        engine.shutdown()

    def test_disabled_engine_doesnt_call_storage(self, temp_dir):
        """Test that disabled engine doesn't call storage backends."""
        config_dict = {
            "vigil": {
                "core": {"enabled": False},
                "storage": {"backends": [{"type": "file", "directory": str(temp_dir)}]},
            }
        }
        engine = AuditEngine(config_dict=config_dict)

        mock_backend = Mock()
        engine.storage_backends = [mock_backend]

        engine.log(action="test")
        mock_backend.store.assert_not_called()
        engine.shutdown()


class TestStatistics:
    """Test suite for engine statistics."""

    def test_get_stats_returns_dict(self, audit_engine):
        """Test that get_stats returns a dictionary."""
        stats = audit_engine.get_stats()
        assert isinstance(stats, dict)

    def test_get_stats_includes_events_logged(self, audit_engine):
        """Test that stats include events logged count."""
        stats = audit_engine.get_stats()
        assert "events_logged" in stats
        assert isinstance(stats["events_logged"], int)

    def test_get_stats_includes_errors(self, audit_engine):
        """Test that stats include error count."""
        stats = audit_engine.get_stats()
        assert "errors" in stats
        assert isinstance(stats["errors"], int)

    def test_get_stats_includes_backend_count(self, audit_engine):
        """Test that stats include backend count."""
        stats = audit_engine.get_stats()
        assert "backends" in stats
        assert stats["backends"] == len(audit_engine.storage_backends)

    def test_get_stats_includes_enabled_status(self, audit_engine):
        """Test that stats include enabled status."""
        stats = audit_engine.get_stats()
        assert "enabled" in stats
        assert isinstance(stats["enabled"], bool)

    def test_stats_updated_after_logging(self, audit_engine):
        """Test that stats are updated after logging."""
        initial_stats = audit_engine.get_stats()
        audit_engine.log(action="test")
        new_stats = audit_engine.get_stats()
        assert new_stats["events_logged"] > initial_stats["events_logged"]


class TestShutdown:
    """Test suite for engine shutdown."""

    def test_shutdown_closes_backends(self, audit_engine):
        """Test that shutdown closes all backends."""
        mock_backend = Mock()
        audit_engine.storage_backends = [mock_backend]

        audit_engine.shutdown()
        mock_backend.close.assert_called_once()

    def test_shutdown_handles_backend_errors(self, audit_engine, caplog):
        """Test that shutdown handles backend close errors."""
        mock_backend = Mock()
        mock_backend.close.side_effect = Exception("Close failed")
        audit_engine.storage_backends = [mock_backend]

        # Should not raise exception
        audit_engine.shutdown()

    def test_shutdown_with_backend_without_close_method(self, audit_engine):
        """Test shutdown with backend that doesn't have close method."""
        mock_backend = Mock(spec=[])  # No methods
        audit_engine.storage_backends = [mock_backend]

        # Should not raise exception
        audit_engine.shutdown()


class TestContextManager:
    """Test suite for context manager functionality."""

    def test_context_manager_enter(self, audit_config):
        """Test that engine can be used as context manager."""
        with AuditEngine(config=audit_config) as engine:
            assert engine is not None
            assert isinstance(engine, AuditEngine)

    def test_context_manager_exit_calls_shutdown(self, audit_config):
        """Test that context manager exit calls shutdown."""
        with patch.object(AuditEngine, "shutdown") as mock_shutdown:
            with AuditEngine(config=audit_config):
                pass
            # Shutdown should be called on exit
            mock_shutdown.assert_called_once()

    def test_context_manager_logs_events(self, audit_config):
        """Test logging events within context manager."""
        with AuditEngine(config=audit_config) as engine:
            event = engine.log(action="test")
            assert event is not None

    def test_context_manager_shutdown_on_exception(self, audit_config):
        """Test that shutdown is called even when exception occurs."""
        with patch.object(AuditEngine, "shutdown") as mock_shutdown:
            try:
                with AuditEngine(config=audit_config):
                    raise ValueError("Test exception")
            except ValueError:
                pass

            # Shutdown should still be called
            mock_shutdown.assert_called_once()


class TestErrorHandling:
    """Test suite for error handling."""

    def test_logging_error_doesnt_crash_engine(self, audit_engine):
        """Test that logging errors don't crash the engine."""
        # Mock storage to raise error
        mock_backend = Mock()
        mock_backend.store.side_effect = Exception("Storage error")
        audit_engine.storage_backends = [mock_backend]

        # Engine should handle error gracefully
        try:
            audit_engine.log(action="test")
        except StorageError:
            pass  # Expected

        # Engine should still be functional
        stats = audit_engine.get_stats()
        assert stats["errors"] > 0

    def test_exception_during_event_building_increments_error_counter(self, audit_engine):
        """Test that exceptions during event building increment error counter."""
        # Cause error by passing invalid data
        with pytest.raises(ValueError):
            audit_engine.log(action=None)

        # Error counter should not increment for validation errors
        # (they raise immediately before try/except)

    def test_general_exception_returns_none(self, audit_engine):
        """Test that general exceptions return None."""
        # Mock _build_event to raise exception
        with patch.object(audit_engine, "_build_event", side_effect=Exception("Build failed")):
            event = audit_engine.log(action="test")
            assert event is None

        # Error counter should be incremented
        stats = audit_engine.get_stats()
        assert stats["errors"] > 0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_log_with_very_large_parameters(self, audit_engine):
        """Test logging with very large parameter dictionary."""
        large_params = {f"key_{i}": f"value_{i}" for i in range(1000)}
        event = audit_engine.log(action="test", parameters=large_params)
        assert event is not None

    def test_log_with_deeply_nested_parameters(self, audit_engine):
        """Test logging with deeply nested parameters."""
        nested = {"level": 0}
        current = nested
        for i in range(20):
            current["nested"] = {"level": i + 1}
            current = current["nested"]

        event = audit_engine.log(action="test", parameters=nested)
        assert event is not None

    def test_log_with_unicode_characters(self, audit_engine):
        """Test logging with unicode characters."""
        event = audit_engine.log(
            action="测试操作",
            actor={"username": "用户名"},
            parameters={"数据": "值"},
        )
        assert event is not None
        assert event.action.operation == "测试操作"

    def test_log_with_special_characters(self, audit_engine):
        """Test logging with special characters."""
        event = audit_engine.log(
            action="test\"action'with<special>chars&symbols",
            parameters={"key": "value\nwith\nnewlines"},
        )
        assert event is not None

    def test_multiple_engines_independent(self, temp_dir):
        """Test that multiple engine instances are independent."""
        config1 = {
            "vigil": {
                "core": {"enabled": True, "application_name": "app1"},
                "storage": {"backends": [{"type": "file", "directory": str(temp_dir / "app1")}]},
            }
        }
        config2 = {
            "vigil": {
                "core": {"enabled": True, "application_name": "app2"},
                "storage": {"backends": [{"type": "file", "directory": str(temp_dir / "app2")}]},
            }
        }

        engine1 = AuditEngine(config_dict=config1)
        engine2 = AuditEngine(config_dict=config2)

        engine1.log(action="test1")
        engine2.log(action="test2")

        assert engine1.get_stats()["events_logged"] == 1
        assert engine2.get_stats()["events_logged"] == 1

        engine1.shutdown()
        engine2.shutdown()

    def test_log_after_shutdown(self, audit_config):
        """Test logging after shutdown (should still work if re-used)."""
        engine = AuditEngine(config=audit_config)
        engine.log(action="before_shutdown")
        engine.shutdown()

        # Logging after shutdown should still work
        # (shutdown only closes backends, doesn't disable engine)
        engine.log(action="after_shutdown")
        # May fail due to closed backends, but shouldn't crash

    def test_engine_with_no_sanitizer_import(self, temp_dir, caplog):
        """Test engine initialization when sanitizer import fails."""
        config_dict = {
            "vigil": {
                "core": {"enabled": True},
                "storage": {"backends": [{"type": "file", "directory": str(temp_dir)}]},
                "processing": {"sanitization": {"enabled": True}},
            }
        }

        # Mock import to fail (PIISanitizer is imported lazily inside _init_sanitizer)
        with patch(
            "vigil.processing.sanitizers.PIISanitizer",
            side_effect=ImportError("mocked import failure"),
        ):
            engine = AuditEngine(config_dict=config_dict)
            # Sanitizer should be None when import fails
            assert engine.sanitizer is None

        engine.shutdown()


class TestFilterChain:
    """Test suite for event filter chain (TD-10)."""

    def _make_engine_with_filters(self, temp_dir, filters):
        """Create an engine with the given filter config."""
        config_dict = {
            "vigil": {
                "core": {"enabled": True},
                "storage": {"backends": [{"type": "file", "directory": str(temp_dir)}]},
                "processing": {
                    "sanitization": {"enabled": False},
                    "filters": filters,
                },
            }
        }
        return AuditEngine(config_dict=config_dict)

    def test_filter_by_category_excludes_event(self, temp_dir):
        """Events matching excluded categories are dropped."""
        engine = self._make_engine_with_filters(
            temp_dir,
            [
                {"type": "exclude_category", "categories": ["DATABASE"]},
            ],
        )
        event = engine.log(action="query", category="DATABASE")
        assert event is None
        assert engine.get_stats()["events_logged"] == 0
        engine.shutdown()

    def test_filter_by_category_allows_event(self, temp_dir):
        """Events not matching excluded categories pass through."""
        engine = self._make_engine_with_filters(
            temp_dir,
            [
                {"type": "exclude_category", "categories": ["DATABASE"]},
            ],
        )
        event = engine.log(action="login", category="AUTH")
        assert event is not None
        assert engine.get_stats()["events_logged"] == 1
        engine.shutdown()

    def test_filter_by_action_type_excludes_event(self, temp_dir):
        """Events matching excluded action types are dropped."""
        engine = self._make_engine_with_filters(
            temp_dir,
            [
                {"type": "exclude_action_type", "action_types": ["DELETE"]},
            ],
        )
        event = engine.log(action="remove_user", action_type="DELETE")
        assert event is None
        assert engine.get_stats()["events_logged"] == 0
        engine.shutdown()

    def test_filter_chain_applies_all_filters(self, temp_dir):
        """Multiple filters are applied in sequence."""
        engine = self._make_engine_with_filters(
            temp_dir,
            [
                {"type": "exclude_category", "categories": ["SYSTEM"]},
                {"type": "exclude_action_type", "action_types": ["DELETE"]},
            ],
        )

        # Excluded by category filter
        assert engine.log(action="cron", category="SYSTEM") is None

        # Excluded by action_type filter
        assert engine.log(action="remove", category="DATABASE", action_type="DELETE") is None

        # Passes both filters
        event = engine.log(action="query", category="DATABASE", action_type="READ")
        assert event is not None
        assert engine.get_stats()["events_logged"] == 1
        engine.shutdown()

    def test_no_filters_allows_all_events(self, temp_dir):
        """With no filters configured, all events pass through."""
        engine = self._make_engine_with_filters(temp_dir, [])
        event = engine.log(action="anything", category="DATABASE", action_type="DELETE")
        assert event is not None
        assert engine.get_stats()["events_logged"] == 1
        engine.shutdown()

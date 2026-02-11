"""Unit tests for audit event data models.

Tests cover:
- Event serialization (to_dict, to_json)
- Event deserialization (from_dict, from_json)
- Timestamp validation (format, bounds checking)
- Nested object serialization
- Field exclusion of None values
- Edge cases and error handling
"""

import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from vigil.core.event import (
    ActionContext,
    ActionResult,
    ActorContext,
    AuditEvent,
    ErrorInfo,
    PerformanceMetrics,
    ResourceInfo,
    SessionContext,
)


class TestSessionContext:
    """Test suite for SessionContext data model."""

    def test_session_context_creation(self):
        """Test creating SessionContext with all fields."""
        session = SessionContext(
            session_id="session-123",
            request_id="request-456",
            correlation_id="corr-789",
        )
        assert session.session_id == "session-123"
        assert session.request_id == "request-456"
        assert session.correlation_id == "corr-789"

    def test_session_context_defaults(self):
        """Test SessionContext default values."""
        session = SessionContext()
        assert session.session_id is None
        assert session.request_id is None
        assert session.correlation_id is None

    def test_session_context_to_dict_excludes_none(self):
        """Test that to_dict excludes None values."""
        session = SessionContext(session_id="session-123")
        result = session.to_dict()
        assert "session_id" in result
        assert result["session_id"] == "session-123"
        assert "request_id" not in result
        assert "correlation_id" not in result

    def test_session_context_to_dict_includes_all_fields(self):
        """Test that to_dict includes all non-None fields."""
        session = SessionContext(
            session_id="session-123",
            request_id="request-456",
            correlation_id="corr-789",
        )
        result = session.to_dict()
        assert len(result) == 3
        assert result["session_id"] == "session-123"
        assert result["request_id"] == "request-456"
        assert result["correlation_id"] == "corr-789"


class TestActorContext:
    """Test suite for ActorContext data model."""

    def test_actor_context_creation(self):
        """Test creating ActorContext with all fields."""
        actor = ActorContext(
            type="user",
            id="user-123",
            username="testuser",
            email="test@example.com",
            roles=["admin", "user"],
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )
        assert actor.type == "user"
        assert actor.id == "user-123"
        assert actor.username == "testuser"
        assert actor.email == "test@example.com"
        assert actor.roles == ["admin", "user"]
        assert actor.ip_address == "192.168.1.1"
        assert actor.user_agent == "Mozilla/5.0"

    def test_actor_context_defaults(self):
        """Test ActorContext default values."""
        actor = ActorContext()
        assert actor.type == "anonymous"
        assert actor.id is None
        assert actor.username is None
        assert actor.email is None
        assert actor.roles == []
        assert actor.ip_address is None
        assert actor.user_agent is None

    def test_actor_context_to_dict_excludes_none(self):
        """Test that to_dict excludes None values."""
        actor = ActorContext(username="testuser")
        result = actor.to_dict()
        assert "username" in result
        assert "type" in result  # Has default value
        assert "id" not in result
        assert "email" not in result

    def test_actor_context_empty_roles_list(self):
        """Test that empty roles list is included in dict."""
        actor = ActorContext(roles=[])
        result = actor.to_dict()
        # Empty list is not None, so it should be included
        assert "roles" in result
        assert result["roles"] == []


class TestResourceInfo:
    """Test suite for ResourceInfo data model."""

    def test_resource_info_creation(self):
        """Test creating ResourceInfo with all fields."""
        resource = ResourceInfo(
            type="table",
            id="table-123",
            name="users",
            path="/db/users",
        )
        assert resource.type == "table"
        assert resource.id == "table-123"
        assert resource.name == "users"
        assert resource.path == "/db/users"

    def test_resource_info_defaults(self):
        """Test ResourceInfo default values."""
        resource = ResourceInfo()
        assert resource.type is None
        assert resource.id is None
        assert resource.name is None
        assert resource.path is None

    def test_resource_info_to_dict_excludes_none(self):
        """Test that to_dict excludes None values."""
        resource = ResourceInfo(name="users")
        result = resource.to_dict()
        assert "name" in result
        assert result["name"] == "users"
        assert "type" not in result
        assert "id" not in result
        assert "path" not in result


class TestActionResult:
    """Test suite for ActionResult data model."""

    def test_action_result_creation(self):
        """Test creating ActionResult with all fields."""
        result_obj = ActionResult(
            status="SUCCESS",
            code="200",
            message="Operation successful",
            rows_affected=5,
            data_size_bytes=1024,
        )
        assert result_obj.status == "SUCCESS"
        assert result_obj.code == "200"
        assert result_obj.message == "Operation successful"
        assert result_obj.rows_affected == 5
        assert result_obj.data_size_bytes == 1024

    def test_action_result_defaults(self):
        """Test ActionResult default values."""
        result_obj = ActionResult()
        assert result_obj.status == "SUCCESS"
        assert result_obj.code is None
        assert result_obj.message is None
        assert result_obj.rows_affected is None
        assert result_obj.data_size_bytes is None

    def test_action_result_failure_status(self):
        """Test ActionResult with FAILURE status."""
        result_obj = ActionResult(status="FAILURE", message="Error occurred")
        assert result_obj.status == "FAILURE"
        assert result_obj.message == "Error occurred"


class TestActionContext:
    """Test suite for ActionContext data model."""

    def test_action_context_creation(self):
        """Test creating ActionContext with all fields."""
        action = ActionContext(
            type="READ",
            category="DATABASE",
            operation="select_query",
            description="Retrieve user data",
            parameters={"query": "SELECT * FROM users"},
        )
        assert action.type == "READ"
        assert action.category == "DATABASE"
        assert action.operation == "select_query"
        assert action.description == "Retrieve user data"
        assert action.parameters == {"query": "SELECT * FROM users"}

    def test_action_context_defaults(self):
        """Test ActionContext default values."""
        action = ActionContext()
        assert action.type == "EXECUTE"
        assert action.category == "SYSTEM"
        assert action.operation is None
        assert isinstance(action.resource, ResourceInfo)
        assert action.description is None
        assert action.parameters == {}
        assert isinstance(action.result, ActionResult)

    def test_action_context_to_dict_nested_objects(self):
        """Test that to_dict properly converts nested objects."""
        action = ActionContext(
            type="WRITE",
            category="DATABASE",
            operation="insert",
        )
        result = action.to_dict()
        assert "type" in result
        assert "category" in result
        assert "resource" in result
        assert isinstance(result["resource"], dict)
        assert "result" in result
        assert isinstance(result["result"], dict)


class TestPerformanceMetrics:
    """Test suite for PerformanceMetrics data model."""

    def test_performance_metrics_creation(self):
        """Test creating PerformanceMetrics with all fields."""
        metrics = PerformanceMetrics(
            duration_ms=123.45,
            cpu_time_ms=100.0,
            memory_mb=50.5,
            slow_query=True,
            threshold_exceeded=True,
        )
        assert metrics.duration_ms == 123.45
        assert metrics.cpu_time_ms == 100.0
        assert metrics.memory_mb == 50.5
        assert metrics.slow_query is True
        assert metrics.threshold_exceeded is True

    def test_performance_metrics_defaults(self):
        """Test PerformanceMetrics default values."""
        metrics = PerformanceMetrics()
        assert metrics.duration_ms is None
        assert metrics.cpu_time_ms is None
        assert metrics.memory_mb is None
        assert metrics.slow_query is False
        assert metrics.threshold_exceeded is False

    def test_performance_metrics_to_dict_includes_booleans(self):
        """Test that to_dict includes boolean fields even when False."""
        metrics = PerformanceMetrics(duration_ms=50.0)
        result = metrics.to_dict()
        assert "duration_ms" in result
        # Booleans with default False are not None, so included
        assert "slow_query" in result
        assert "threshold_exceeded" in result


class TestErrorInfo:
    """Test suite for ErrorInfo data model."""

    def test_error_info_creation(self):
        """Test creating ErrorInfo with all fields."""
        error = ErrorInfo(
            occurred=True,
            type="ValueError",
            message="Invalid input",
            stack_trace="Traceback...",
            handled=False,
        )
        assert error.occurred is True
        assert error.type == "ValueError"
        assert error.message == "Invalid input"
        assert error.stack_trace == "Traceback..."
        assert error.handled is False

    def test_error_info_defaults(self):
        """Test ErrorInfo default values."""
        error = ErrorInfo()
        assert error.occurred is False
        assert error.type is None
        assert error.message is None
        assert error.stack_trace is None
        assert error.handled is True


class TestAuditEvent:
    """Test suite for AuditEvent data model."""

    def test_event_default_timestamp_is_timezone_aware(self):
        """Test that default timestamp is timezone-aware UTC (TD-07)."""
        event = AuditEvent()
        assert event.timestamp.tzinfo is not None
        assert event.timestamp.tzinfo == timezone.utc

    def test_from_dict_timezone_aware_timestamp_accepted(self):
        """Test that timezone-aware timestamps are accepted without error (TD-07)."""
        aware_ts = datetime.now(timezone.utc).isoformat()
        data = {"timestamp": aware_ts}
        event = AuditEvent.from_dict(data)
        assert isinstance(event.timestamp, datetime)

    def test_from_dict_naive_timestamp_accepted(self):
        """Test that naive timestamps are still accepted (treated as UTC) (TD-07)."""
        naive_ts = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        data = {"timestamp": naive_ts}
        event = AuditEvent.from_dict(data)
        assert isinstance(event.timestamp, datetime)

    def test_audit_event_creation_defaults(self):
        """Test creating AuditEvent with default values."""
        event = AuditEvent()
        assert isinstance(event.event_id, str)
        assert UUID(event.event_id)  # Valid UUID
        assert isinstance(event.timestamp, datetime)
        assert event.version == "1.0.0"
        assert isinstance(event.session, SessionContext)
        assert isinstance(event.actor, ActorContext)
        assert isinstance(event.action, ActionContext)
        assert isinstance(event.performance, PerformanceMetrics)
        assert isinstance(event.error, ErrorInfo)
        assert event.system == {}
        assert event.custom == {}
        assert event.metadata == {}

    def test_audit_event_with_custom_fields(self):
        """Test creating AuditEvent with custom fields."""
        event = AuditEvent(
            system={"hostname": "server1"},
            custom={"request_source": "api"},
            metadata={"app": "test_app"},
        )
        assert event.system == {"hostname": "server1"}
        assert event.custom == {"request_source": "api"}
        assert event.metadata == {"app": "test_app"}

    def test_audit_event_to_dict(self):
        """Test converting AuditEvent to dictionary."""
        event = AuditEvent()
        event.actor.username = "testuser"
        event.action.operation = "test_operation"

        result = event.to_dict()

        assert "event_id" in result
        assert "timestamp" in result
        assert "version" in result
        assert "session" in result
        assert "actor" in result
        assert "action" in result
        assert "performance" in result
        assert "error" in result
        assert "system" in result
        assert "custom" in result
        assert "metadata" in result

        # Check nested objects are dicts
        assert isinstance(result["session"], dict)
        assert isinstance(result["actor"], dict)
        assert isinstance(result["action"], dict)

        # Check timestamp is ISO format string
        assert isinstance(result["timestamp"], str)
        assert "T" in result["timestamp"]

    def test_audit_event_to_json(self):
        """Test converting AuditEvent to JSON string."""
        event = AuditEvent()
        event.actor.username = "testuser"

        json_str = event.to_json()
        assert isinstance(json_str, str)

        # Parse JSON to verify it's valid
        parsed = json.loads(json_str)
        assert "event_id" in parsed
        assert "timestamp" in parsed
        assert parsed["actor"]["username"] == "testuser"

    def test_audit_event_to_json_with_indent(self):
        """Test converting AuditEvent to pretty-printed JSON."""
        event = AuditEvent()
        json_str = event.to_json(indent=2)
        assert isinstance(json_str, str)
        assert "\n" in json_str  # Pretty-printed has newlines
        assert "  " in json_str  # Has indentation

    def test_audit_event_from_dict(self, sample_event_dict):
        """Test creating AuditEvent from dictionary."""
        event = AuditEvent.from_dict(sample_event_dict)

        assert event.event_id == "test-event-123"
        assert isinstance(event.timestamp, datetime)
        assert event.version == "1.0.0"
        assert event.actor.username == "testuser"
        assert event.action.operation == "select_query"

    def test_audit_event_from_dict_with_datetime_object(self):
        """Test from_dict with datetime object instead of string."""
        now = datetime.now(timezone.utc)
        data = {
            "timestamp": now,
            "actor": {"username": "test"},
        }
        event = AuditEvent.from_dict(data)
        assert event.timestamp == now

    def test_audit_event_from_json(self):
        """Test creating AuditEvent from JSON string."""
        json_str = json.dumps(
            {
                "event_id": "json-event-123",
                "timestamp": "2024-01-15T10:30:00",
                "version": "1.0.0",
                "actor": {"username": "jsonuser"},
                "action": {"operation": "json_op"},
            }
        )

        event = AuditEvent.from_json(json_str)
        assert event.event_id == "json-event-123"
        assert event.actor.username == "jsonuser"
        assert event.action.operation == "json_op"

    def test_audit_event_roundtrip_dict(self):
        """Test that to_dict/from_dict is reversible."""
        original = AuditEvent()
        original.actor.username = "roundtrip_user"
        original.action.operation = "roundtrip_op"
        original.custom = {"key": "value"}

        # Convert to dict and back
        event_dict = original.to_dict()
        restored = AuditEvent.from_dict(event_dict)

        assert restored.event_id == original.event_id
        assert restored.actor.username == original.actor.username
        assert restored.action.operation == original.action.operation
        assert restored.custom == original.custom

    def test_audit_event_roundtrip_json(self):
        """Test that to_json/from_json is reversible."""
        original = AuditEvent()
        original.actor.username = "json_roundtrip"

        # Convert to JSON and back
        json_str = original.to_json()
        restored = AuditEvent.from_json(json_str)

        assert restored.event_id == original.event_id
        assert restored.actor.username == original.actor.username


class TestTimestampValidation:
    """Test suite for timestamp validation in AuditEvent.from_dict."""

    def test_valid_timestamp_iso_format(self):
        """Test that valid ISO timestamp is parsed correctly."""
        data = {
            "timestamp": "2024-01-15T10:30:00",
        }
        event = AuditEvent.from_dict(data)
        assert isinstance(event.timestamp, datetime)
        assert event.timestamp.year == 2024
        assert event.timestamp.month == 1
        assert event.timestamp.day == 15

    def test_valid_timestamp_with_microseconds(self):
        """Test timestamp with microseconds."""
        data = {
            "timestamp": "2024-01-15T10:30:00.123456",
        }
        event = AuditEvent.from_dict(data)
        assert isinstance(event.timestamp, datetime)
        assert event.timestamp.microsecond == 123456

    def test_valid_timestamp_with_timezone(self):
        """Test timestamp with timezone info."""
        data = {
            "timestamp": "2024-01-15T10:30:00+00:00",
        }
        event = AuditEvent.from_dict(data)
        assert isinstance(event.timestamp, datetime)

    def test_invalid_timestamp_format(self):
        """Test that invalid timestamp format raises ValueError."""
        data = {
            "timestamp": "invalid-timestamp",
        }
        with pytest.raises(ValueError) as exc_info:
            AuditEvent.from_dict(data)
        assert "Invalid timestamp format" in str(exc_info.value)

    def test_timestamp_too_far_in_future(self):
        """Test that timestamp too far in future is rejected."""
        future_time = datetime.now(timezone.utc) + timedelta(hours=2)
        data = {
            "timestamp": future_time.isoformat(),
        }
        with pytest.raises(ValueError) as exc_info:
            AuditEvent.from_dict(data)
        assert "too far in the future" in str(exc_info.value)

    def test_timestamp_within_allowed_future_skew(self):
        """Test that timestamp within 1 hour future is allowed (clock skew)."""
        # 30 minutes in future should be OK
        future_time = datetime.now(timezone.utc) + timedelta(minutes=30)
        data = {
            "timestamp": future_time.isoformat(),
        }
        event = AuditEvent.from_dict(data)
        assert isinstance(event.timestamp, datetime)

    def test_timestamp_exactly_1_hour_future(self):
        """Test timestamp exactly at 1 hour future boundary."""
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        data = {
            "timestamp": future_time.isoformat(),
        }
        # Should be accepted (<=1 hour allowed)
        event = AuditEvent.from_dict(data)
        assert isinstance(event.timestamp, datetime)

    def test_timestamp_too_far_in_past(self):
        """Test that timestamp more than 100 years in past is rejected."""
        past_time = datetime.now(timezone.utc) - timedelta(days=365 * 101)
        data = {
            "timestamp": past_time.isoformat(),
        }
        with pytest.raises(ValueError) as exc_info:
            AuditEvent.from_dict(data)
        assert "too far in the past" in str(exc_info.value)

    def test_timestamp_99_years_past_is_valid(self):
        """Test that timestamp 99 years in past is accepted."""
        past_time = datetime.now(timezone.utc) - timedelta(days=365 * 99)
        data = {
            "timestamp": past_time.isoformat(),
        }
        event = AuditEvent.from_dict(data)
        assert isinstance(event.timestamp, datetime)

    def test_timestamp_malformed_string(self):
        """Test various malformed timestamp strings."""
        malformed_timestamps = [
            "2024-13-01T10:30:00",  # Invalid month
            "2024-01-32T10:30:00",  # Invalid day
            "2024-01-15T25:30:00",  # Invalid hour
            "not-a-date",
            "12345",
            "",
        ]

        for ts in malformed_timestamps:
            data = {"timestamp": ts}
            with pytest.raises(ValueError):
                AuditEvent.from_dict(data)


class TestNestedObjectSerialization:
    """Test nested object serialization and deserialization."""

    def test_nested_resource_info_serialization(self):
        """Test that nested ResourceInfo is properly serialized."""
        event = AuditEvent()
        event.action.resource.type = "table"
        event.action.resource.name = "users"

        result = event.to_dict()
        assert "action" in result
        assert "resource" in result["action"]
        assert result["action"]["resource"]["type"] == "table"
        assert result["action"]["resource"]["name"] == "users"

    def test_nested_resource_info_deserialization(self):
        """Test that nested ResourceInfo is properly deserialized."""
        data = {
            "action": {
                "type": "READ",
                "category": "DATABASE",
                "resource": {
                    "type": "table",
                    "name": "users",
                },
            },
        }
        event = AuditEvent.from_dict(data)
        assert isinstance(event.action.resource, ResourceInfo)
        assert event.action.resource.type == "table"
        assert event.action.resource.name == "users"

    def test_nested_action_result_serialization(self):
        """Test that nested ActionResult is properly serialized."""
        event = AuditEvent()
        event.action.result.status = "SUCCESS"
        event.action.result.rows_affected = 10

        result = event.to_dict()
        assert "action" in result
        assert "result" in result["action"]
        assert result["action"]["result"]["status"] == "SUCCESS"
        assert result["action"]["result"]["rows_affected"] == 10

    def test_nested_action_result_deserialization(self):
        """Test that nested ActionResult is properly deserialized."""
        data = {
            "action": {
                "type": "WRITE",
                "category": "DATABASE",
                "result": {
                    "status": "FAILURE",
                    "message": "Constraint violation",
                },
            },
        }
        event = AuditEvent.from_dict(data)
        assert isinstance(event.action.result, ActionResult)
        assert event.action.result.status == "FAILURE"
        assert event.action.result.message == "Constraint violation"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_event_dict(self):
        """Test creating event from empty dictionary."""
        event = AuditEvent.from_dict({})
        assert isinstance(event, AuditEvent)
        assert isinstance(event.event_id, str)

    def test_event_with_extra_fields(self):
        """Test that extra fields in dict don't cause errors."""
        data = {
            "extra_field": "extra_value",
            "another_field": 123,
        }
        # Should not raise an error
        event = AuditEvent.from_dict(data)
        assert isinstance(event, AuditEvent)

    def test_event_with_none_values(self):
        """Test event with explicit None values."""
        data = {
            "custom": None,
            "metadata": None,
            "system": None,
        }
        event = AuditEvent.from_dict(data)
        # None values should be replaced with empty dicts by defaults
        assert event.custom is None or event.custom == {}
        assert event.metadata is None or event.metadata == {}
        assert event.system is None or event.system == {}

    def test_very_large_event(self):
        """Test event with very large custom data."""
        large_data = {"key_" + str(i): "value_" + str(i) for i in range(1000)}
        event = AuditEvent(custom=large_data)

        # Should be able to serialize
        result = event.to_dict()
        assert len(result["custom"]) == 1000

        # Should be able to deserialize
        restored = AuditEvent.from_dict(result)
        assert len(restored.custom) == 1000

    def test_unicode_in_event(self):
        """Test event with unicode characters."""
        event = AuditEvent()
        event.actor.username = "用户名"
        event.action.operation = "操作"
        event.custom = {"emoji": "🔒🔐"}

        # Should serialize and deserialize correctly
        json_str = event.to_json()
        restored = AuditEvent.from_json(json_str)
        assert restored.actor.username == "用户名"
        assert restored.action.operation == "操作"
        assert restored.custom["emoji"] == "🔒🔐"

    def test_special_characters_in_strings(self):
        """Test event with special characters."""
        event = AuditEvent()
        event.action.operation = "test\nwith\nnewlines"
        event.custom = {"quotes": 'test "quotes" here'}

        # Should serialize and deserialize correctly
        json_str = event.to_json()
        restored = AuditEvent.from_json(json_str)
        assert restored.action.operation == "test\nwith\nnewlines"
        assert restored.custom["quotes"] == 'test "quotes" here'

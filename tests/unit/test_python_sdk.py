"""Unit tests for the Python SDK client.

Tests cover:
- Single event logging (log)
- Batch event logging (log_batch)
- AuditEvent object logging (log_audit_event)
- Auth header propagation
- Error handling (401, 500)
- Context manager lifecycle
- Auto-generated timestamps and event IDs
- Application/environment metadata injection
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock

import pytest

from sdks.python.audit_sdk.client import AuditClient


@pytest.fixture
def mock_response():
    """Create a mock successful HTTP response."""
    resp = Mock()
    resp.status_code = 201
    resp.json.return_value = {"status": "accepted", "event_id": "test-id"}
    resp.raise_for_status = Mock()
    return resp


@pytest.fixture
def mock_session(mock_response):
    """Create a mock requests.Session."""
    session = MagicMock()
    session.post.return_value = mock_response
    session.headers = {}
    return session


@pytest.fixture
def client(mock_session):
    """Create an AuditClient with a mocked HTTP session."""
    c = AuditClient(
        collector_url="http://localhost:8080",
        api_key="test-key-123",
        application="test-app",
        environment="test",
    )
    c.session = mock_session
    return c


class TestClientInitialization:
    """Test suite for AuditClient initialization."""

    def test_base_url_strips_trailing_slash(self):
        """Test that trailing slashes are removed from collector URL."""
        c = AuditClient(collector_url="http://localhost:8080/")
        assert c.base_url == "http://localhost:8080"

    def test_auth_header_is_set(self):
        """Test that Authorization header is set when api_key is provided."""
        c = AuditClient(collector_url="http://localhost:8080", api_key="my-key")
        assert c.session.headers["Authorization"] == "Bearer my-key"

    def test_no_auth_header_without_key(self):
        """Test that no Authorization header is set when api_key is empty."""
        c = AuditClient(collector_url="http://localhost:8080", api_key="")
        assert "Authorization" not in c.session.headers

    def test_content_type_header_is_json(self):
        """Test that Content-Type is set to application/json."""
        c = AuditClient(collector_url="http://localhost:8080")
        assert c.session.headers["Content-Type"] == "application/json"

    def test_default_timeout(self):
        """Test that default timeout is 10 seconds."""
        c = AuditClient(collector_url="http://localhost:8080")
        assert c.timeout == 10

    def test_custom_timeout(self):
        """Test that custom timeout is respected."""
        c = AuditClient(collector_url="http://localhost:8080", timeout=30)
        assert c.timeout == 30


class TestLog:
    """Test suite for AuditClient.log()."""

    def test_log_sends_event(self, client, mock_session):
        """Test that log() sends a POST request with correct event payload."""
        client.log(
            action_type="READ",
            action_category="DATABASE",
            operation="query_users",
        )

        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert call_args[0][0] == "http://localhost:8080/api/v1/events"
        payload = call_args[1]["json"]
        assert payload["action"]["type"] == "READ"
        assert payload["action"]["category"] == "DATABASE"
        assert payload["action"]["operation"] == "query_users"

    def test_log_auto_generates_timestamp(self, client, mock_session):
        """Test that log() auto-generates a UTC timestamp when not provided."""
        client.log(action_type="EXECUTE", operation="test")

        payload = mock_session.post.call_args[1]["json"]
        assert "timestamp" in payload
        # Verify it's a valid ISO timestamp
        ts = datetime.fromisoformat(payload["timestamp"])
        assert ts.tzinfo is not None

    def test_log_auto_generates_event_id(self, client, mock_session):
        """Test that log() auto-generates a UUID event_id."""
        client.log(action_type="EXECUTE", operation="test")

        payload = mock_session.post.call_args[1]["json"]
        assert "event_id" in payload
        assert len(payload["event_id"]) == 36  # UUID format

    def test_log_includes_actor(self, client, mock_session):
        """Test that log() includes actor context when provided."""
        client.log(
            operation="test",
            actor={"type": "user", "username": "admin"},
        )

        payload = mock_session.post.call_args[1]["json"]
        assert payload["actor"]["type"] == "user"
        assert payload["actor"]["username"] == "admin"

    def test_log_includes_metadata_with_app_and_env(self, client, mock_session):
        """Test that log() injects application and environment into metadata."""
        client.log(operation="test")

        payload = mock_session.post.call_args[1]["json"]
        assert payload["metadata"]["application"] == "test-app"
        assert payload["metadata"]["environment"] == "test"

    def test_log_includes_custom_metadata(self, client, mock_session):
        """Test that custom metadata is merged with app/env metadata."""
        client.log(operation="test", metadata={"custom_key": "custom_value"})

        payload = mock_session.post.call_args[1]["json"]
        assert payload["metadata"]["custom_key"] == "custom_value"
        assert payload["metadata"]["application"] == "test-app"

    def test_log_includes_optional_fields(self, client, mock_session):
        """Test that optional fields are included when provided."""
        client.log(
            operation="test",
            resource={"type": "table", "name": "users"},
            result={"status": "SUCCESS"},
            parameters={"query": "SELECT *"},
            performance={"duration_ms": 42.5},
            error={"occurred": True, "message": "timeout"},
            custom={"trace_id": "abc-123"},
        )

        payload = mock_session.post.call_args[1]["json"]
        assert payload["action"]["resource"]["name"] == "users"
        assert payload["action"]["result"]["status"] == "SUCCESS"
        assert payload["action"]["parameters"]["query"] == "SELECT *"
        assert payload["performance"]["duration_ms"] == 42.5
        assert payload["error"]["message"] == "timeout"
        assert payload["custom"]["trace_id"] == "abc-123"

    def test_log_raises_on_auth_error(self, client, mock_session):
        """Test that log() raises when server returns 401."""
        from requests.exceptions import HTTPError

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = HTTPError(response=Mock(status_code=401))
        mock_session.post.return_value = mock_response

        with pytest.raises(HTTPError):
            client.log(operation="test")

    def test_log_raises_on_server_error(self, client, mock_session):
        """Test that log() raises when server returns 500."""
        from requests.exceptions import HTTPError

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = HTTPError(response=Mock(status_code=500))
        mock_session.post.return_value = mock_response

        with pytest.raises(HTTPError):
            client.log(operation="test")


class TestLogBatch:
    """Test suite for AuditClient.log_batch()."""

    def test_log_batch_sends_events(self, client, mock_session):
        """Test that log_batch() sends a POST to /events/batch."""
        mock_session.post.return_value.json.return_value = {
            "status": "accepted",
            "accepted": 2,
            "errors": [],
            "event_ids": ["id-1", "id-2"],
        }

        events = [
            {"action": {"type": "READ", "category": "DATABASE"}},
            {"action": {"type": "WRITE", "category": "API"}},
        ]
        client.log_batch(events)

        call_args = mock_session.post.call_args
        assert "/api/v1/events/batch" in call_args[0][0]
        payload = call_args[1]["json"]
        assert "events" in payload
        assert len(payload["events"]) == 2

    def test_log_batch_auto_generates_ids_and_timestamps(self, client, mock_session):
        """Test that log_batch() fills in missing event_id and timestamp."""
        mock_session.post.return_value.json.return_value = {
            "status": "accepted",
            "accepted": 1,
            "errors": [],
            "event_ids": ["x"],
        }

        events = [{"action": {"type": "READ", "category": "DATABASE"}}]
        client.log_batch(events)

        assert "event_id" in events[0]
        assert "timestamp" in events[0]

    def test_log_batch_preserves_existing_ids(self, client, mock_session):
        """Test that log_batch() preserves existing event_id and timestamp."""
        mock_session.post.return_value.json.return_value = {
            "status": "accepted",
            "accepted": 1,
            "errors": [],
            "event_ids": ["x"],
        }

        events = [
            {
                "event_id": "my-custom-id",
                "timestamp": "2024-01-15T10:00:00+00:00",
                "action": {"type": "READ", "category": "DATABASE"},
            }
        ]
        client.log_batch(events)

        assert events[0]["event_id"] == "my-custom-id"
        assert events[0]["timestamp"] == "2024-01-15T10:00:00+00:00"


class TestLogAuditEvent:
    """Test suite for AuditClient.log_audit_event()."""

    def test_log_audit_event_sends_event_dict(self, client, mock_session):
        """Test that log_audit_event() sends the AuditEvent's dict representation."""
        from vigil.core.event import AuditEvent

        event = AuditEvent()
        event.actor.username = "sdk-test-user"
        event.action.operation = "sdk_test_op"

        client.log_audit_event(event)

        call_args = mock_session.post.call_args
        assert "/api/v1/events" in call_args[0][0]
        payload = call_args[1]["json"]
        assert payload["actor"]["username"] == "sdk-test-user"
        assert payload["action"]["operation"] == "sdk_test_op"
        assert "event_id" in payload
        assert "timestamp" in payload


class TestContextManager:
    """Test suite for AuditClient context manager."""

    def test_context_manager_closes_session(self):
        """Test that exiting context manager closes the HTTP session."""
        mock_sess = MagicMock()
        client = AuditClient(collector_url="http://localhost:8080")
        client.session = mock_sess

        with client:
            pass

        mock_sess.close.assert_called_once()

    def test_context_manager_with_mock(self, mock_session):
        """Test that context manager calls close on session."""
        client = AuditClient(collector_url="http://localhost:8080")
        client.session = mock_session

        client.close()

        mock_session.close.assert_called_once()

    def test_enter_returns_self(self):
        """Test that __enter__ returns the client instance."""
        client = AuditClient(collector_url="http://localhost:8080")
        result = client.__enter__()
        assert result is client
        client.close()


class TestEdgeCases:
    """Edge case tests for AuditClient — network failures, timeouts, boundaries."""

    def test_log_raises_on_connect_timeout(self, client, mock_session):
        """Test that log() raises ConnectTimeout when connection hangs."""
        from requests.exceptions import ConnectTimeout

        mock_session.post.side_effect = ConnectTimeout("Connection timed out")

        with pytest.raises(ConnectTimeout):
            client.log(operation="test")

    def test_log_raises_on_read_timeout(self, client, mock_session):
        """Test that log() raises ReadTimeout when server is too slow."""
        from requests.exceptions import ReadTimeout

        mock_session.post.side_effect = ReadTimeout("Read timed out")

        with pytest.raises(ReadTimeout):
            client.log(operation="test")

    def test_log_raises_on_connection_refused(self, client, mock_session):
        """Test that log() raises ConnectionError when collector is unreachable."""
        from requests.exceptions import ConnectionError as ReqConnectionError

        mock_session.post.side_effect = ReqConnectionError("Connection refused")

        with pytest.raises(ReqConnectionError):
            client.log(operation="test")

    def test_log_handles_invalid_json_response(self, client, mock_session):
        """Test that log() raises when server returns invalid JSON."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.side_effect = ValueError("No JSON object could be decoded")
        mock_session.post.return_value = mock_response

        with pytest.raises(ValueError):
            client.log(operation="test")

    def test_log_batch_empty_list(self, client, mock_session):
        """Test that log_batch() sends POST even with empty events list."""
        mock_session.post.return_value.json.return_value = {
            "status": "accepted",
            "accepted": 0,
            "errors": [],
            "event_ids": [],
        }

        client.log_batch([])

        call_args = mock_session.post.call_args
        payload = call_args[1]["json"]
        assert payload["events"] == []

    def test_log_batch_max_size(self, client, mock_session):
        """Test that log_batch() sends all 100 events in a single request."""
        mock_session.post.return_value.json.return_value = {
            "status": "accepted",
            "accepted": 100,
            "errors": [],
            "event_ids": [f"id-{i}" for i in range(100)],
        }

        events = [{"action": {"type": "READ", "category": "DATABASE"}} for _ in range(100)]
        client.log_batch(events)

        call_args = mock_session.post.call_args
        payload = call_args[1]["json"]
        assert len(payload["events"]) == 100

    def test_log_preserves_unicode(self, client, mock_session):
        """Test that unicode characters are preserved in event payload."""
        client.log(
            operation="query_users",
            actor={"type": "user", "username": "utilisateur\u00e9"},
            custom={"description": "\u65e5\u672c\u8a9e\u30c6\u30b9\u30c8"},
        )

        payload = mock_session.post.call_args[1]["json"]
        assert payload["actor"]["username"] == "utilisateur\u00e9"
        assert payload["custom"]["description"] == "\u65e5\u672c\u8a9e\u30c6\u30b9\u30c8"

    def test_log_uses_custom_event_id_and_timestamp(self, client, mock_session):
        """Test that log() uses custom event_id and timestamp instead of auto-generating."""
        client.log(
            operation="test",
            event_id="my-custom-event-id",
            timestamp="2024-06-15T12:00:00+00:00",
        )

        payload = mock_session.post.call_args[1]["json"]
        assert payload["event_id"] == "my-custom-event-id"
        assert payload["timestamp"] == "2024-06-15T12:00:00+00:00"

    def test_session_reused_across_calls(self, client, mock_session):
        """Test that the same session is reused for multiple log() calls."""
        client.log(operation="call-1")
        client.log(operation="call-2")

        assert mock_session.post.call_count == 2

    def test_base_url_strips_multiple_trailing_slashes(self):
        """Test that multiple trailing slashes are stripped from collector URL."""
        c = AuditClient(collector_url="http://localhost:8080///")
        assert c.base_url == "http://localhost:8080"

    def test_user_metadata_takes_precedence(self, client, mock_session):
        """Test that user-provided metadata keys are not overwritten by app/env defaults."""
        client.log(
            operation="test",
            metadata={"application": "user-override", "environment": "user-env"},
        )

        payload = mock_session.post.call_args[1]["json"]
        assert payload["metadata"]["application"] == "user-override"
        assert payload["metadata"]["environment"] == "user-env"

    def test_log_audit_event_invalid_object(self, client):
        """Test that log_audit_event() raises AttributeError for invalid objects."""
        with pytest.raises(AttributeError):
            client.log_audit_event("not-an-audit-event")

    def test_log_batch_raises_on_connection_error(self, client, mock_session):
        """Test that log_batch() raises ConnectionError on network failure."""
        from requests.exceptions import ConnectionError as ReqConnectionError

        mock_session.post.side_effect = ReqConnectionError("Connection refused")

        with pytest.raises(ReqConnectionError):
            client.log_batch([{"action": {"type": "READ", "category": "DB"}}])

    def test_timeout_passed_to_requests(self, client, mock_session):
        """Test that the configured timeout is forwarded to session.post()."""
        client.timeout = 30
        client.log(operation="test")

        call_args = mock_session.post.call_args
        assert call_args[1]["timeout"] == 30

    def test_context_manager_closes_on_exception(self):
        """Test that session is closed even when exception occurs in with block."""
        mock_sess = MagicMock()
        c = AuditClient(collector_url="http://localhost:8080")
        c.session = mock_sess

        with pytest.raises(ValueError):
            with c:
                raise ValueError("something broke")

        mock_sess.close.assert_called_once()

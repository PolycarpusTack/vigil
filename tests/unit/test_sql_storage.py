"""Tests for SQL storage backend."""

import pytest

try:
    import sqlalchemy  # noqa: F401

    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False

pytestmark = pytest.mark.skipif(not HAS_SQLALCHEMY, reason="sqlalchemy not installed")

from vigil.core.event import (  # noqa: E402
    ActionContext,
    ActionResult,
    ActorContext,
    AuditEvent,
    ResourceInfo,
)
from vigil.storage.sql_storage import SQLStorageBackend  # noqa: E402


@pytest.fixture
def sql_backend(tmp_path):
    """Create a SQL storage backend with SQLite for testing."""
    db_path = tmp_path / "test_audit.db"
    backend = SQLStorageBackend({"url": f"sqlite:///{db_path}", "echo": False})
    yield backend
    backend.close()


@pytest.fixture
def sample_event():
    """Create a sample audit event."""
    event = AuditEvent()
    event.actor = ActorContext(type="user", username="testuser", email="test@example.com")
    event.action = ActionContext(
        type="READ",
        category="DATABASE",
        operation="query_users",
        resource=ResourceInfo(type="table", name="users"),
        result=ActionResult(status="SUCCESS", rows_affected=10),
    )
    event.metadata = {"application": "test-app", "environment": "test"}
    return event


class TestSQLStorageBackend:
    def test_init_creates_table(self, sql_backend):
        """Backend initializes and creates the audit_events table."""
        from sqlalchemy import inspect

        inspector = inspect(sql_backend.engine)
        tables = inspector.get_table_names()
        assert "audit_events" in tables

    def test_store_event(self, sql_backend, sample_event):
        """Events can be stored and retrieved."""
        sql_backend.store(sample_event)

        result = sql_backend.get_event(sample_event.event_id)
        assert result is not None
        assert result["event_id"] == sample_event.event_id
        assert result["actor"]["username"] == "testuser"
        assert result["action"]["category"] == "DATABASE"

    def test_store_multiple_events(self, sql_backend):
        """Multiple events can be stored."""
        events = []
        for i in range(5):
            event = AuditEvent()
            event.actor = ActorContext(type="user", username=f"user{i}")
            event.action = ActionContext(type="EXECUTE", category="SYSTEM", operation=f"op{i}")
            event.metadata = {"application": "test-app", "environment": "test"}
            events.append(event)

        for event in events:
            sql_backend.store(event)

        assert sql_backend.count() == 5

    def test_query_with_filters(self, sql_backend):
        """Events can be filtered by column values."""
        for cat in ["DATABASE", "API", "DATABASE"]:
            event = AuditEvent()
            event.action = ActionContext(type="READ", category=cat, operation="test")
            event.metadata = {"application": "test-app", "environment": "test"}
            sql_backend.store(event)

        db_events = sql_backend.query(filters={"action_category": "DATABASE"})
        assert len(db_events) == 2

    def test_query_pagination(self, sql_backend):
        """Query supports limit and offset."""
        for i in range(10):
            event = AuditEvent()
            event.action = ActionContext(type="EXECUTE", category="SYSTEM", operation=f"op{i}")
            event.metadata = {"application": "app", "environment": "test"}
            sql_backend.store(event)

        page1 = sql_backend.query(limit=3, offset=0)
        page2 = sql_backend.query(limit=3, offset=3)
        assert len(page1) == 3
        assert len(page2) == 3
        assert page1[0]["event_id"] != page2[0]["event_id"]

    def test_get_nonexistent_event(self, sql_backend):
        """Getting a nonexistent event returns None."""
        result = sql_backend.get_event("nonexistent-id")
        assert result is None

    def test_count(self, sql_backend, sample_event):
        """Count returns correct number of events."""
        assert sql_backend.count() == 0
        sql_backend.store(sample_event)
        assert sql_backend.count() == 1

    def test_event_data_round_trip(self, sql_backend, sample_event):
        """Full event data is preserved through storage round-trip."""
        sql_backend.store(sample_event)
        stored = sql_backend.get_event(sample_event.event_id)

        original = sample_event.to_dict()
        assert stored["event_id"] == original["event_id"]
        assert stored["version"] == original["version"]
        assert stored["actor"] == original["actor"]
        assert stored["action"] == original["action"]
        assert stored["metadata"] == original["metadata"]

    def test_close(self, tmp_path):
        """Backend can be closed cleanly."""
        db_path = tmp_path / "close_test.db"
        backend = SQLStorageBackend({"url": f"sqlite:///{db_path}"})
        backend.close()

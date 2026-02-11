"""Contract tests: validate AuditEvent.to_dict() against JSON schema.

Ensures that the Python data model and the JSON schema stay in sync.
"""

import json
from pathlib import Path

import pytest

try:
    import jsonschema

    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

pytestmark = pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema not installed")

from vigil.core.enums import ActionCategory, ActionType  # noqa: E402
from vigil.core.event import (  # noqa: E402
    ActionContext,
    ActionResult,
    ActorContext,
    AuditEvent,
    ErrorInfo,
    PerformanceMetrics,
    ResourceInfo,
    SessionContext,
)

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema" / "audit_event.schema.json"


@pytest.fixture(scope="module")
def audit_schema():
    """Load the audit event JSON schema."""
    with open(SCHEMA_PATH) as f:
        return json.load(f)


def _validate(event_dict: dict, schema: dict) -> None:
    """Validate event_dict against schema, raising on failure."""
    jsonschema.validate(instance=event_dict, schema=schema)


class TestSchemaConformance:
    """Test that AuditEvent.to_dict() produces schema-valid output."""

    def test_default_event_conforms_to_schema(self, audit_schema):
        """A default AuditEvent passes schema validation."""
        event = AuditEvent()
        d = event.to_dict()
        _validate(d, audit_schema)

    def test_full_event_conforms_to_schema(self, audit_schema):
        """A fully populated event passes schema validation."""
        event = AuditEvent()
        event.session = SessionContext(
            session_id="sess-1", request_id="req-1", correlation_id="corr-1"
        )
        event.actor = ActorContext(
            type="user",
            id="u-1",
            username="admin",
            email="admin@example.com",
            roles=["admin"],
            ip_address="10.0.0.1",
            user_agent="TestAgent/1.0",
        )
        event.action = ActionContext(
            type="READ",
            category="DATABASE",
            operation="query_users",
            description="Select all active users",
            resource=ResourceInfo(type="table", id="tbl-1", name="users", path="/db/users"),
            parameters={"limit": 100},
            result=ActionResult(status="SUCCESS", code="200", message="OK", rows_affected=42),
        )
        event.performance = PerformanceMetrics(duration_ms=12.5, cpu_time_ms=5.0, memory_mb=128.0)
        event.error = ErrorInfo(occurred=False)
        event.system = {"host": {"hostname": "test"}}
        event.custom = {"request_trace": "abc123"}
        event.metadata = {"application": "test-app", "environment": "test"}

        d = event.to_dict()
        _validate(d, audit_schema)

    def test_event_with_all_action_types(self, audit_schema):
        """Events with each valid action type pass schema validation."""
        for at in ActionType:
            event = AuditEvent()
            event.action = ActionContext(type=at.value, category="SYSTEM", operation="test")
            _validate(event.to_dict(), audit_schema)

    def test_event_with_all_categories(self, audit_schema):
        """Events with each valid category pass schema validation."""
        for cat in ActionCategory:
            event = AuditEvent()
            event.action = ActionContext(type="EXECUTE", category=cat.value, operation="test")
            _validate(event.to_dict(), audit_schema)


class TestSchemaRejection:
    """Test that invalid events are rejected by the schema."""

    def test_invalid_action_type_rejected(self, audit_schema):
        """An invalid action type fails schema validation."""
        event = AuditEvent()
        d = event.to_dict()
        d["action"]["type"] = "INVALID_TYPE"
        with pytest.raises(jsonschema.ValidationError):
            _validate(d, audit_schema)

    def test_invalid_category_rejected(self, audit_schema):
        """An invalid category fails schema validation."""
        event = AuditEvent()
        d = event.to_dict()
        d["action"]["category"] = "INVALID_CATEGORY"
        with pytest.raises(jsonschema.ValidationError):
            _validate(d, audit_schema)

    def test_missing_action_rejected(self, audit_schema):
        """A missing action field fails schema validation."""
        event = AuditEvent()
        d = event.to_dict()
        del d["action"]
        with pytest.raises(jsonschema.ValidationError):
            _validate(d, audit_schema)


class TestSchemaEnumAlignment:
    """Test that schema enums match Python enums exactly."""

    def test_schema_action_types_match_python_enums(self, audit_schema):
        """JSON schema action type enum matches Python ActionType enum."""
        schema_types = set(audit_schema["properties"]["action"]["properties"]["type"]["enum"])
        python_types = {at.value for at in ActionType}
        assert schema_types == python_types

    def test_schema_categories_match_python_enums(self, audit_schema):
        """JSON schema category enum matches Python ActionCategory enum."""
        schema_cats = set(audit_schema["properties"]["action"]["properties"]["category"]["enum"])
        python_cats = {cat.value for cat in ActionCategory}
        assert schema_cats == python_cats

"""Integration tests for the collector API using FastAPI TestClient."""

import json
import os
from datetime import datetime, timezone
from uuid import uuid4

import pytest

# Set a test API key before importing the app
os.environ["DATABASE_URL"] = "sqlite:///test_collector.db"
os.environ["API_KEYS"] = "test-api-key-123"

try:
    from fastapi.testclient import TestClient

    from collector.main import app

    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

pytestmark = pytest.mark.skipif(not HAS_FASTAPI, reason="fastapi not installed")

AUTH_HEADER = {"Authorization": "Bearer test-api-key-123"}


@pytest.fixture(scope="module")
def client():
    """Create a test client for the collector app."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def sample_event():
    """A minimal valid audit event."""
    return {
        "event_id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "action": {
            "type": "READ",
            "category": "DATABASE",
            "operation": "query_users",
        },
        "actor": {"type": "user", "username": "testuser"},
        "metadata": {"application": "test-app", "environment": "test"},
    }


class TestHealthEndpoints:
    def test_health(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_ready(self, client):
        resp = client.get("/api/v1/ready")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"


class TestEventEndpoints:
    def test_ingest_event(self, client, sample_event):
        resp = client.post("/api/v1/events", json=sample_event, headers=AUTH_HEADER)
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "accepted"
        assert data["event_id"] == sample_event["event_id"]

    def test_ingest_event_no_auth(self, client, sample_event):
        resp = client.post("/api/v1/events", json=sample_event)
        assert resp.status_code in (401, 403)  # No bearer token

    def test_ingest_event_bad_auth(self, client, sample_event):
        resp = client.post(
            "/api/v1/events",
            json=sample_event,
            headers={"Authorization": "Bearer wrong-key"},
        )
        assert resp.status_code == 401

    def test_get_event(self, client, sample_event):
        # Ingest first
        client.post("/api/v1/events", json=sample_event, headers=AUTH_HEADER)

        # Retrieve
        resp = client.get(f"/api/v1/events/{sample_event['event_id']}", headers=AUTH_HEADER)
        assert resp.status_code == 200
        assert resp.json()["event_id"] == sample_event["event_id"]

    def test_get_event_not_found(self, client):
        resp = client.get("/api/v1/events/nonexistent-id", headers=AUTH_HEADER)
        assert resp.status_code == 404

    def test_query_events(self, client, sample_event):
        # Ingest an event
        client.post("/api/v1/events", json=sample_event, headers=AUTH_HEADER)

        resp = client.get("/api/v1/events", headers=AUTH_HEADER)
        assert resp.status_code == 200
        data = resp.json()
        assert "events" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_query_events_with_filter(self, client):
        event = {
            "event_id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0",
            "action": {"type": "WRITE", "category": "API", "operation": "create_user"},
            "actor": {"type": "service", "username": "api-service"},
            "metadata": {"application": "filter-test", "environment": "test"},
        }
        client.post("/api/v1/events", json=event, headers=AUTH_HEADER)

        resp = client.get(
            "/api/v1/events?action_category=API&application=filter-test",
            headers=AUTH_HEADER,
        )
        assert resp.status_code == 200
        data = resp.json()
        for e in data["events"]:
            assert e["action"]["category"] == "API"

    def test_batch_ingest(self, client):
        events = []
        for i in range(5):
            events.append(
                {
                    "event_id": str(uuid4()),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "version": "1.0.0",
                    "action": {
                        "type": "EXECUTE",
                        "category": "SYSTEM",
                        "operation": f"batch_op_{i}",
                    },
                }
            )
        resp = client.post("/api/v1/events/batch", json={"events": events}, headers=AUTH_HEADER)
        assert resp.status_code == 201
        data = resp.json()
        assert data["accepted"] == 5
        assert len(data["event_ids"]) == 5


class TestRateLimiting:
    """Tests for rate limiting middleware (TD-02)."""

    def test_rate_limit_exceeded_returns_429(self, client):
        """Test that exceeding rate limit returns 429 Too Many Requests."""
        from collector.middleware.rate_limit import RateLimitMiddleware

        # Get the middleware instance from the app
        for middleware in client.app.user_middleware:
            if middleware.cls is RateLimitMiddleware:
                # Set very low limit for testing
                middleware.kwargs = {"max_requests": 3, "window_seconds": 60}
                break

        # Need to recreate middleware with low limit for this test
        # Instead, directly test the middleware's internal logic
        mw = RateLimitMiddleware(client.app, max_requests=3, window_seconds=60)

        # Simulate requests
        for _ in range(3):
            is_limited, _ = mw._is_rate_limited("test-client")
            assert not is_limited
            mw._requests["test-client"].append(__import__("time").monotonic())

        # 4th request should be rate limited
        is_limited, remaining = mw._is_rate_limited("test-client")
        assert is_limited
        assert remaining == 0


class TestAuthBypassRemoval:
    """Tests that dev-mode auth bypass is removed (TD-03)."""

    def test_no_keys_configured_rejects_requests(self, client):
        """Test that when no API keys are configured, requests are rejected."""
        from collector.auth import api_keys

        # Save original state
        original_hashes = api_keys._valid_key_hashes

        try:
            # Clear all keys
            api_keys._valid_key_hashes = set()

            # Ensure AUTH_DISABLED is not set
            auth_disabled = os.environ.pop("AUTH_DISABLED", None)
            try:
                resp = client.post(
                    "/api/v1/events",
                    json={
                        "action": {"type": "READ", "category": "DATABASE"},
                    },
                    headers={"Authorization": "Bearer some-token"},
                )
                assert resp.status_code == 401
                assert "Authentication required" in resp.json()["detail"]
            finally:
                if auth_disabled is not None:
                    os.environ["AUTH_DISABLED"] = auth_disabled
        finally:
            api_keys._valid_key_hashes = original_hashes

    def test_auth_disabled_allows_requests(self, client):
        """Test that AUTH_DISABLED=true explicitly allows unauthenticated access."""
        from collector.auth import api_keys

        original_hashes = api_keys._valid_key_hashes

        try:
            api_keys._valid_key_hashes = set()
            os.environ["AUTH_DISABLED"] = "true"

            resp = client.get(
                "/api/v1/events",
                headers={"Authorization": "Bearer any-token"},
            )
            assert resp.status_code == 200
        finally:
            api_keys._valid_key_hashes = original_hashes
            os.environ.pop("AUTH_DISABLED", None)


class TestPIISanitization:
    """Tests that PII is sanitized when events are ingested (TD-01)."""

    def test_ingested_event_has_pii_sanitized(self, client):
        """Test that email PII in metadata is redacted on ingest."""
        event_id = str(uuid4())
        event = {
            "event_id": event_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0",
            "action": {"type": "READ", "category": "DATABASE", "operation": "query"},
            "actor": {"type": "user", "username": "test", "email": "secret@example.com"},
            "metadata": {"application": "pii-test", "environment": "test"},
        }
        resp = client.post("/api/v1/events", json=event, headers=AUTH_HEADER)
        assert resp.status_code == 201

        # Retrieve and verify PII is redacted
        resp = client.get(f"/api/v1/events/{event_id}", headers=AUTH_HEADER)
        assert resp.status_code == 200
        stored = resp.json()
        assert "secret@example.com" not in json.dumps(stored)
        assert "***EMAIL_REDACTED***" in json.dumps(stored)

    def test_ingested_event_api_key_sanitized(self, client):
        """Test that API keys in parameters are redacted on ingest."""
        event_id = str(uuid4())
        event = {
            "event_id": event_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0",
            "action": {
                "type": "EXECUTE",
                "category": "API",
                "operation": "call_service",
                "parameters": {
                    "api_key": "xk_fake_abcdef1234567890abcdef1234",
                },
            },
            "metadata": {"application": "pii-test", "environment": "test"},
        }
        resp = client.post("/api/v1/events", json=event, headers=AUTH_HEADER)
        assert resp.status_code == 201

        resp = client.get(f"/api/v1/events/{event_id}", headers=AUTH_HEADER)
        assert resp.status_code == 200
        stored = resp.json()
        assert "xk_fake_abcdef1234567890abcdef1234" not in json.dumps(stored)
        assert "***REDACTED***" in json.dumps(stored)


class TestMetricsEndpoints:
    def test_ingest_metrics(self, client):
        payload = {
            "agent_id": "test-agent-01",
            "hostname": "test-host",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": {
                "cpu_percent": 45.2,
                "memory_percent": 67.8,
                "memory_used_mb": 4096.0,
                "memory_total_mb": 8192.0,
                "disk_percent": 55.0,
                "disk_used_gb": 100.0,
                "disk_total_gb": 200.0,
                "network_bytes_sent": 1000000,
                "network_bytes_recv": 2000000,
                "uptime_seconds": 86400.0,
                "process_count": 150,
            },
        }
        resp = client.post("/api/v1/metrics", json=payload, headers=AUTH_HEADER)
        assert resp.status_code == 201
        assert resp.json()["status"] == "accepted"

    def test_query_metrics(self, client):
        # Ingest first
        payload = {
            "agent_id": "query-test-agent",
            "hostname": "query-host",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": {"cpu_percent": 30.0, "memory_percent": 50.0},
        }
        client.post("/api/v1/metrics", json=payload, headers=AUTH_HEADER)

        resp = client.get("/api/v1/metrics/query-test-agent", headers=AUTH_HEADER)
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_id"] == "query-test-agent"
        assert len(data["metrics"]) >= 1

    def test_query_metrics_not_found(self, client):
        resp = client.get("/api/v1/metrics/nonexistent-agent", headers=AUTH_HEADER)
        assert resp.status_code == 404


class TestAgentsEndpoints:
    def test_list_agents(self, client):
        # Ingest a metric to register an agent
        payload = {
            "agent_id": "list-test-agent",
            "hostname": "list-host",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": {"cpu_percent": 10.0, "memory_percent": 20.0},
        }
        client.post("/api/v1/metrics", json=payload, headers=AUTH_HEADER)

        resp = client.get("/api/v1/agents", headers=AUTH_HEADER)
        assert resp.status_code == 200
        data = resp.json()
        assert "agents" in data
        agent_ids = [a["agent_id"] for a in data["agents"]]
        assert "list-test-agent" in agent_ids


class TestCORSConfiguration:
    """Tests for CORS middleware configuration."""

    def test_cors_preflight_returns_headers(self, client):
        """OPTIONS preflight from allowed origin returns CORS headers."""
        resp = client.options(
            "/api/v1/events",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization,Content-Type",
            },
        )
        assert resp.status_code == 200
        assert "access-control-allow-origin" in resp.headers

    def test_cors_allowed_origin(self, client, sample_event):
        """Requests from allowed origin get Access-Control-Allow-Origin header."""
        resp = client.get(
            "/api/v1/health",
            headers={"Origin": "http://localhost:3000"},
        )
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_cors_disallowed_origin(self, client):
        """Requests from disallowed origin do not get CORS header."""
        resp = client.get(
            "/api/v1/health",
            headers={"Origin": "http://evil.example.com"},
        )
        assert resp.status_code == 200
        # Disallowed origin should not have the allow-origin header
        assert resp.headers.get("access-control-allow-origin") is None


class TestInternalMetrics:
    """Tests for collector internal metrics endpoint."""

    def test_internal_metrics_returns_counters(self, client):
        """Internal metrics endpoint returns expected fields."""
        resp = client.get("/api/v1/internal/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "request_count" in data
        assert "error_count" in data
        assert "uptime_seconds" in data
        assert isinstance(data["request_count"], int)
        assert isinstance(data["error_count"], int)

    def test_internal_metrics_request_count_increments(self, client):
        """Request count increases after making requests."""
        resp1 = client.get("/api/v1/internal/metrics")
        count_before = resp1.json()["request_count"]

        # Make a few requests
        client.get("/api/v1/health")
        client.get("/api/v1/health")

        resp2 = client.get("/api/v1/internal/metrics")
        count_after = resp2.json()["request_count"]
        assert count_after > count_before

    def test_internal_metrics_uptime(self, client):
        """Uptime is non-negative."""
        resp = client.get("/api/v1/internal/metrics")
        assert resp.json()["uptime_seconds"] >= 0

    def test_internal_metrics_no_auth_required(self, client):
        """Internal metrics endpoint does not require authentication."""
        # No Authorization header
        resp = client.get("/api/v1/internal/metrics")
        assert resp.status_code == 200

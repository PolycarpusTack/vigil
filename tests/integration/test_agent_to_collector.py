"""Integration test: agent sends metrics to collector.

Tests cover:
- Full metric cycle (collect real metrics → POST → GET → verify)
- HTTPSender retry behavior with mocked collector responses
- HTTPSender failure modes (4xx, 5xx, connection errors)
- Agent health tracking across success/failure cycles
- collect_all_metrics payload structure
"""

import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///test_agent_collector.db")
os.environ.setdefault("API_KEYS", "test-api-key-123")

try:
    import psutil  # noqa: F401
    from fastapi.testclient import TestClient

    from collector.main import app

    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

pytestmark = pytest.mark.skipif(not HAS_DEPS, reason="fastapi or psutil not installed")

from agent.collectors.cpu import collect_cpu  # noqa: E402
from agent.collectors.disk import collect_disk  # noqa: E402
from agent.collectors.memory import collect_memory  # noqa: E402
from agent.collectors.network import collect_network  # noqa: E402
from agent.collectors.process import collect_top_processes  # noqa: E402
from agent.collectors.uptime import collect_uptime  # noqa: E402
from agent.config import AgentConfig  # noqa: E402
from agent.transport.http_sender import HTTPSender  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


AUTH = {"Authorization": "Bearer test-api-key-123"}


class TestAgentToCollector:
    def test_full_metric_cycle(self, client):
        """Collect real metrics and push them through the collector API."""
        cpu = collect_cpu()
        mem = collect_memory()
        disk = collect_disk()
        net = collect_network()
        procs = collect_top_processes(count=3)
        uptime = collect_uptime()

        payload = {
            "agent_id": "integration-test-agent",
            "hostname": "test-host",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": {
                "cpu_percent": cpu,
                **mem,
                **disk,
                **net,
                "uptime_seconds": uptime,
                **procs,
            },
        }

        # POST metrics
        resp = client.post("/api/v1/metrics", json=payload, headers=AUTH)
        assert resp.status_code == 201

        # GET metrics back
        resp = client.get("/api/v1/metrics/integration-test-agent", headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 1
        entry = data["metrics"][0]
        assert entry["metrics"]["cpu_percent"] == cpu
        assert entry["metrics"]["memory_percent"] == mem["memory_percent"]

        # Agent should appear in agents list
        resp = client.get("/api/v1/agents", headers=AUTH)
        assert resp.status_code == 200
        agent_ids = [a["agent_id"] for a in resp.json()["agents"]]
        assert "integration-test-agent" in agent_ids


class TestHTTPSenderWithMockedCollector:
    """Integration tests for HTTPSender retry/failure behavior with mocked HTTP."""

    @pytest.fixture
    def sender(self):
        """Create an HTTPSender with fast backoff for testing."""
        s = HTTPSender(
            collector_url="http://localhost:9999",
            api_key="test-key",
            max_retries=3,
            backoff_base=0.01,  # Fast backoff for tests
        )
        yield s
        s.close()

    def test_sender_succeeds_on_201(self, sender):
        """Test that send_metrics returns True when collector returns 201."""
        mock_resp = Mock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"status": "accepted"}
        sender.session.post = Mock(return_value=mock_resp)

        payload = {"agent_id": "test", "hostname": "h", "metrics": {"cpu_percent": 50.0}}
        result = sender.send_metrics(payload)

        assert result is True
        sender.session.post.assert_called_once()

    @patch("agent.transport.http_sender.time.sleep")
    def test_sender_retries_on_500_then_succeeds(self, mock_sleep, sender):
        """Test that sender retries on 500 and succeeds on next attempt."""
        resp_500 = Mock()
        resp_500.status_code = 500
        resp_500.text = "Internal Server Error"

        resp_201 = Mock()
        resp_201.status_code = 201
        resp_201.json.return_value = {"status": "accepted"}

        sender.session.post = Mock(side_effect=[resp_500, resp_201])

        result = sender.send_metrics({"agent_id": "t", "metrics": {"cpu_percent": 1}})

        assert result is True
        assert sender.session.post.call_count == 2

    @patch("agent.transport.http_sender.time.sleep")
    def test_sender_fails_after_max_retries(self, mock_sleep, sender):
        """Test that sender returns False after exhausting all retry attempts."""
        resp_500 = Mock()
        resp_500.status_code = 500
        resp_500.text = "Internal Server Error"

        sender.session.post = Mock(return_value=resp_500)

        result = sender.send_metrics({"agent_id": "t", "metrics": {"cpu_percent": 1}})

        assert result is False
        assert sender.session.post.call_count == 3

    def test_sender_no_retry_on_401(self, sender):
        """Test that 401 returns False immediately without retrying."""
        resp_401 = Mock()
        resp_401.status_code = 401
        resp_401.text = "Unauthorized"

        sender.session.post = Mock(return_value=resp_401)

        result = sender.send_metrics({"agent_id": "t", "metrics": {"cpu_percent": 1}})

        assert result is False
        sender.session.post.assert_called_once()

    @patch("agent.transport.http_sender.time.sleep")
    def test_sender_retries_on_429(self, mock_sleep, sender):
        """Test that 429 (rate limited) triggers retry and eventual success."""
        resp_429 = Mock()
        resp_429.status_code = 429
        resp_429.text = "Too Many Requests"

        resp_201 = Mock()
        resp_201.status_code = 201
        resp_201.json.return_value = {"status": "accepted"}

        sender.session.post = Mock(side_effect=[resp_429, resp_201])

        result = sender.send_metrics({"agent_id": "t", "metrics": {"cpu_percent": 1}})

        assert result is True
        assert sender.session.post.call_count == 2

    @patch("agent.transport.http_sender.time.sleep")
    def test_sender_retries_on_connection_error(self, mock_sleep, sender):
        """Test that connection errors trigger retries then return False."""
        import requests

        sender.session.post = Mock(side_effect=requests.ConnectionError("refused"))

        result = sender.send_metrics({"agent_id": "t", "metrics": {"cpu_percent": 1}})

        assert result is False
        assert sender.session.post.call_count == 3


class TestCollectAllMetrics:
    """Integration test for collect_all_metrics payload structure."""

    @patch("agent.main.collect_uptime", return_value=1000.0)
    @patch(
        "agent.main.collect_top_processes",
        return_value={"process_count": 2, "top_processes": []},
    )
    @patch(
        "agent.main.collect_network",
        return_value={"network_bytes_sent": 100, "network_bytes_recv": 200},
    )
    @patch(
        "agent.main.collect_disk",
        return_value={"disk_percent": 55.0, "disk_used_gb": 100, "disk_total_gb": 200},
    )
    @patch(
        "agent.main.collect_memory",
        return_value={
            "memory_percent": 65.0,
            "memory_used_mb": 8000,
            "memory_total_mb": 16000,
        },
    )
    @patch("agent.main.collect_cpu", return_value=42.5)
    def test_collect_all_metrics_has_required_keys(self, *mocks):
        """Test that collect_all_metrics returns payload with all required fields."""
        from agent.main import collect_all_metrics

        config = AgentConfig(agent_id="integration-test", interval_seconds=10)
        payload = collect_all_metrics(config)

        assert payload["agent_id"] == "integration-test"
        assert "hostname" in payload
        assert "timestamp" in payload
        # Verify timestamp is timezone-aware
        ts = datetime.fromisoformat(payload["timestamp"])
        assert ts.tzinfo is not None

        metrics = payload["metrics"]
        assert metrics["cpu_percent"] == 42.5
        assert metrics["memory_percent"] == 65.0
        assert metrics["disk_percent"] == 55.0
        assert metrics["network_bytes_sent"] == 100
        assert metrics["uptime_seconds"] == 1000.0
        assert metrics["process_count"] == 2


class TestAgentRunLoopHealth:
    """Integration test for agent run loop health tracking."""

    @patch("agent.main.time")
    @patch("agent.main.collect_all_metrics")
    @patch("agent.main.HTTPSender")
    def test_run_loop_healthy_on_success(self, mock_sender_cls, mock_collect, mock_time):
        """Test that health is 'healthy' after successful collection cycle."""
        import agent.main as agent_main

        # Setup: one successful cycle then stop
        mock_sender = MagicMock()
        mock_sender.send_metrics.return_value = True
        mock_sender_cls.return_value = mock_sender

        mock_collect.return_value = {"agent_id": "t", "metrics": {"cpu_percent": 1}}

        original_running = agent_main._running
        agent_main._running = True
        call_count = 0

        def stop_after_one(n):
            nonlocal call_count
            call_count += 1
            if call_count >= 1:
                agent_main._running = False

        mock_time.sleep.side_effect = stop_after_one

        config = AgentConfig(
            agent_id="health-test",
            interval_seconds=1,
            collector_url="http://localhost:9999",
        )

        # Patch HealthTracker to capture its state
        with patch("agent.main.HealthTracker") as mock_ht_cls:
            mock_health = MagicMock()
            mock_ht_cls.return_value = mock_health

            agent_main.run(config)

            mock_health.record_success.assert_called_once()
            mock_health.record_failure.assert_not_called()

        agent_main._running = original_running

    @patch("agent.main.time")
    @patch("agent.main.collect_all_metrics")
    @patch("agent.main.HTTPSender")
    def test_run_loop_degraded_on_failures(self, mock_sender_cls, mock_collect, mock_time):
        """Test that health records failures when send_metrics returns False."""
        import agent.main as agent_main

        mock_sender = MagicMock()
        mock_sender.send_metrics.return_value = False
        mock_sender_cls.return_value = mock_sender

        mock_collect.return_value = {"agent_id": "t", "metrics": {"cpu_percent": 1}}

        original_running = agent_main._running
        agent_main._running = True
        call_count = 0

        def stop_after_two(n):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                agent_main._running = False

        mock_time.sleep.side_effect = stop_after_two

        config = AgentConfig(
            agent_id="health-test-fail",
            interval_seconds=1,
            collector_url="http://localhost:9999",
        )

        with patch("agent.main.HealthTracker") as mock_ht_cls:
            mock_health = MagicMock()
            mock_ht_cls.return_value = mock_health

            agent_main.run(config)

            assert mock_health.record_failure.call_count == 2
            mock_health.record_success.assert_not_called()

        agent_main._running = original_running

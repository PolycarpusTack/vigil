"""Unit tests for agent health status tracking.

Tests cover:
- Initial health state
- Status updates after successful sends
- Status updates after failed sends
- Consecutive failure tracking and reset
- Uptime calculation
- Degraded status threshold
"""

import time

from agent.health import HealthTracker


class TestHealthStatusInitial:
    """Tests for initial health state."""

    def test_health_status_initial(self):
        """New tracker reports healthy with no collections."""
        tracker = HealthTracker(agent_id="test-agent")
        status = tracker.get_status()

        assert status["agent_id"] == "test-agent"
        assert status["status"] == "healthy"
        assert status["uptime_seconds"] >= 0
        assert status["last_collection_time"] is None
        assert status["last_send_success"] is None
        assert status["consecutive_failures"] == 0


class TestHealthAfterSend:
    """Tests for status after collection cycles."""

    def test_health_status_after_successful_send(self):
        """Successful send sets last_collection_time and last_send_success."""
        tracker = HealthTracker(agent_id="test-agent")
        tracker.record_success()
        status = tracker.get_status()

        assert status["last_send_success"] is True
        assert status["last_collection_time"] is not None
        assert status["consecutive_failures"] == 0

    def test_health_status_after_failed_send(self):
        """Failed send sets last_send_success to False and increments failures."""
        tracker = HealthTracker(agent_id="test-agent")
        tracker.record_failure()
        status = tracker.get_status()

        assert status["last_send_success"] is False
        assert status["consecutive_failures"] == 1

    def test_consecutive_failures_reset_on_success(self):
        """Consecutive failures reset to 0 after a successful send."""
        tracker = HealthTracker(agent_id="test-agent")
        tracker.record_failure()
        tracker.record_failure()
        tracker.record_failure()

        assert tracker.get_status()["consecutive_failures"] == 3

        tracker.record_success()
        assert tracker.get_status()["consecutive_failures"] == 0


class TestUptime:
    """Tests for uptime calculation."""

    def test_uptime_increases(self):
        """Uptime reflects elapsed time since creation."""
        tracker = HealthTracker(agent_id="test-agent")
        time.sleep(0.05)
        status = tracker.get_status()

        assert status["uptime_seconds"] >= 0.04


class TestStatusField:
    """Tests for the status field (healthy vs degraded)."""

    def test_status_healthy(self):
        """Status is 'healthy' when consecutive_failures is 0."""
        tracker = HealthTracker(agent_id="test-agent")
        tracker.record_success()
        assert tracker.get_status()["status"] == "healthy"

    def test_status_degraded_after_threshold(self):
        """Status is 'degraded' after more than 3 consecutive failures."""
        tracker = HealthTracker(agent_id="test-agent")
        for _ in range(4):
            tracker.record_failure()

        assert tracker.get_status()["status"] == "degraded"

    def test_status_recovers_from_degraded(self):
        """Status returns to 'healthy' after recovery from degraded."""
        tracker = HealthTracker(agent_id="test-agent")
        for _ in range(5):
            tracker.record_failure()
        assert tracker.get_status()["status"] == "degraded"

        tracker.record_success()
        assert tracker.get_status()["status"] == "healthy"

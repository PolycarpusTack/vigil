"""Unit tests for agent main loop.

Tests cover:
- collect_all_metrics builds correct payload
- run() loop sends metrics and handles success/failure
- Signal handling sets _running to False
- main() entry point
"""

import signal
from unittest.mock import MagicMock, patch

from agent.config import AgentConfig


class TestCollectAllMetrics:
    """Tests for collect_all_metrics."""

    @patch("agent.main.collect_uptime", return_value=1000.0)
    @patch(
        "agent.main.collect_top_processes", return_value={"process_count": 5, "top_processes": []}
    )
    @patch(
        "agent.main.collect_network",
        return_value={"network_bytes_sent": 100, "network_bytes_recv": 200},
    )
    @patch(
        "agent.main.collect_disk",
        return_value={"disk_percent": 50.0, "disk_used_gb": 100.0, "disk_total_gb": 200.0},
    )
    @patch(
        "agent.main.collect_memory",
        return_value={"memory_percent": 60.0, "memory_used_mb": 4096.0, "memory_total_mb": 8192.0},
    )
    @patch("agent.main.collect_cpu", return_value=45.0)
    def test_collect_all_metrics_structure(
        self, mock_cpu, mock_mem, mock_disk, mock_net, mock_proc, mock_uptime
    ):
        """collect_all_metrics returns a well-structured payload."""
        from agent.main import collect_all_metrics

        config = AgentConfig(agent_id="test-agent", interval_seconds=10)
        payload = collect_all_metrics(config)

        assert payload["agent_id"] == "test-agent"
        assert "hostname" in payload
        assert "timestamp" in payload
        assert payload["metrics"]["cpu_percent"] == 45.0
        assert payload["metrics"]["memory_percent"] == 60.0
        assert payload["metrics"]["disk_percent"] == 50.0
        assert payload["metrics"]["network_bytes_sent"] == 100
        assert payload["metrics"]["uptime_seconds"] == 1000.0
        assert payload["metrics"]["process_count"] == 5

    @patch("agent.main.collect_uptime", return_value=0.0)
    @patch(
        "agent.main.collect_top_processes", return_value={"process_count": 0, "top_processes": []}
    )
    @patch(
        "agent.main.collect_network",
        return_value={"network_bytes_sent": 0, "network_bytes_recv": 0},
    )
    @patch(
        "agent.main.collect_disk",
        return_value={"disk_percent": 0.0, "disk_used_gb": 0.0, "disk_total_gb": 0.0},
    )
    @patch(
        "agent.main.collect_memory",
        return_value={"memory_percent": 0.0, "memory_used_mb": 0.0, "memory_total_mb": 0.0},
    )
    @patch("agent.main.collect_cpu", return_value=0.0)
    def test_collect_all_metrics_calls_top_processes_with_config(
        self, mock_cpu, mock_mem, mock_disk, mock_net, mock_proc, mock_uptime
    ):
        """collect_all_metrics passes top_processes_count from config."""
        from agent.main import collect_all_metrics

        config = AgentConfig(agent_id="test-agent", top_processes_count=10)
        collect_all_metrics(config)
        mock_proc.assert_called_once_with(count=10)


class TestRunLoop:
    """Tests for the run() main loop."""

    @patch("agent.main.time")
    @patch("agent.main.collect_all_metrics")
    @patch("agent.main.HTTPSender")
    @patch("agent.main.HealthTracker")
    def test_run_sends_metrics_on_success(
        self, mock_health_cls, mock_sender_cls, mock_collect, mock_time
    ):
        """run() calls send_metrics and records success."""
        import agent.main as am

        mock_sender = MagicMock()
        mock_sender.send_metrics.return_value = True
        mock_sender_cls.return_value = mock_sender

        mock_health = MagicMock()
        mock_health_cls.return_value = mock_health

        mock_collect.return_value = {"agent_id": "test", "metrics": {}}

        # Run one loop iteration then stop
        am._running = True
        call_count = 0

        def stop_after_one(seconds):
            nonlocal call_count
            call_count += 1
            if call_count >= 1:
                am._running = False

        mock_time.sleep.side_effect = stop_after_one

        config = AgentConfig(agent_id="test-agent", interval_seconds=1)
        am.run(config)

        mock_sender.send_metrics.assert_called_once()
        mock_health.record_success.assert_called_once()
        mock_sender.close.assert_called_once()

    @patch("agent.main.time")
    @patch("agent.main.collect_all_metrics")
    @patch("agent.main.HTTPSender")
    @patch("agent.main.HealthTracker")
    def test_run_records_failure_on_send_fail(
        self, mock_health_cls, mock_sender_cls, mock_collect, mock_time
    ):
        """run() records failure when send_metrics returns False."""
        import agent.main as am

        mock_sender = MagicMock()
        mock_sender.send_metrics.return_value = False
        mock_sender_cls.return_value = mock_sender

        mock_health = MagicMock()
        mock_health_cls.return_value = mock_health

        mock_collect.return_value = {"agent_id": "test", "metrics": {}}

        am._running = True

        def stop_after_one(seconds):
            am._running = False

        mock_time.sleep.side_effect = stop_after_one

        config = AgentConfig(agent_id="test-agent", interval_seconds=1)
        am.run(config)

        mock_health.record_failure.assert_called_once()

    @patch("agent.main.time")
    @patch("agent.main.collect_all_metrics")
    @patch("agent.main.HTTPSender")
    @patch("agent.main.HealthTracker")
    def test_run_records_failure_on_exception(
        self, mock_health_cls, mock_sender_cls, mock_collect, mock_time
    ):
        """run() records failure when collection raises exception."""
        import agent.main as am

        mock_sender = MagicMock()
        mock_sender_cls.return_value = mock_sender

        mock_health = MagicMock()
        mock_health_cls.return_value = mock_health

        mock_collect.side_effect = RuntimeError("collection failed")

        am._running = True

        def stop_after_one(seconds):
            am._running = False

        mock_time.sleep.side_effect = stop_after_one

        config = AgentConfig(agent_id="test-agent", interval_seconds=1)
        am.run(config)

        mock_health.record_failure.assert_called_once()


class TestSignalHandler:
    """Tests for signal handler."""

    def test_handle_signal_sets_running_false(self):
        """_handle_signal sets _running to False."""
        import agent.main as am

        am._running = True
        am._handle_signal(signal.SIGTERM, None)
        assert am._running is False


class TestMain:
    """Tests for main() entry point."""

    @patch("agent.main.run")
    @patch("agent.main.AgentConfig")
    @patch("agent.main.sys")
    def test_main_no_args_uses_defaults(self, mock_sys, mock_config_cls, mock_run):
        """main() with no args creates default config."""
        from agent.main import main

        mock_sys.argv = ["agent"]
        mock_config = MagicMock()
        mock_config_cls.return_value = mock_config

        main()

        mock_config_cls.assert_called_once_with()
        mock_run.assert_called_once_with(mock_config)

    @patch("agent.main.run")
    @patch("agent.main.AgentConfig")
    @patch("agent.main.sys")
    def test_main_with_config_file(self, mock_sys, mock_config_cls, mock_run):
        """main() with config file arg calls from_yaml."""
        from agent.main import main

        mock_sys.argv = ["agent", "/path/to/config.yaml"]
        mock_config = MagicMock()
        mock_config_cls.from_yaml.return_value = mock_config

        main()

        mock_config_cls.from_yaml.assert_called_once_with("/path/to/config.yaml")
        mock_run.assert_called_once_with(mock_config)

"""Tests for agent metric collectors."""

import pytest

try:
    import psutil  # noqa: F401

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

pytestmark = pytest.mark.skipif(not HAS_PSUTIL, reason="psutil not installed")

from agent.collectors.cpu import collect_cpu  # noqa: E402
from agent.collectors.disk import collect_disk  # noqa: E402
from agent.collectors.memory import collect_memory  # noqa: E402
from agent.collectors.network import collect_network  # noqa: E402
from agent.collectors.process import collect_top_processes  # noqa: E402
from agent.collectors.uptime import collect_uptime  # noqa: E402


class TestCPUCollector:
    def test_returns_float(self):
        result = collect_cpu()
        assert isinstance(result, float)

    def test_range(self):
        result = collect_cpu()
        assert 0 <= result <= 100


class TestMemoryCollector:
    def test_returns_dict(self):
        result = collect_memory()
        assert isinstance(result, dict)

    def test_keys(self):
        result = collect_memory()
        assert "memory_percent" in result
        assert "memory_used_mb" in result
        assert "memory_total_mb" in result

    def test_values_positive(self):
        result = collect_memory()
        assert result["memory_percent"] >= 0
        assert result["memory_used_mb"] > 0
        assert result["memory_total_mb"] > 0


class TestDiskCollector:
    def test_returns_dict(self):
        """Test that collect_disk returns a dictionary."""
        result = collect_disk()
        assert isinstance(result, dict)

    def test_keys(self):
        """Test that collect_disk returns expected keys."""
        result = collect_disk()
        assert "disk_percent" in result
        assert "disk_used_gb" in result
        assert "disk_total_gb" in result

    def test_disk_custom_path(self, tmp_path):
        """Test collect_disk with a custom valid path (TD-05)."""
        result = collect_disk(path=str(tmp_path))
        assert isinstance(result, dict)
        assert "disk_percent" in result
        assert result["disk_total_gb"] > 0

    def test_disk_invalid_path(self):
        """Test collect_disk with an invalid path raises FileNotFoundError (TD-05)."""
        with pytest.raises(FileNotFoundError):
            collect_disk(path="/nonexistent/path/xyz123")

    def test_disk_default_path_cross_platform(self):
        """Test that default path is auto-detected for the current platform (TD-05)."""
        import os

        from agent.collectors.disk import _default_disk_path

        default = _default_disk_path()
        assert os.path.exists(default)


class TestNetworkCollector:
    def test_returns_dict(self):
        result = collect_network()
        assert isinstance(result, dict)

    def test_keys(self):
        result = collect_network()
        assert "network_bytes_sent" in result
        assert "network_bytes_recv" in result

    def test_values_non_negative(self):
        result = collect_network()
        assert result["network_bytes_sent"] >= 0
        assert result["network_bytes_recv"] >= 0


class TestProcessCollector:
    def test_returns_dict(self):
        result = collect_top_processes(count=3)
        assert isinstance(result, dict)

    def test_keys(self):
        result = collect_top_processes(count=3)
        assert "process_count" in result
        assert "top_processes" in result

    def test_top_processes_count(self):
        result = collect_top_processes(count=3)
        assert len(result["top_processes"]) <= 3

    def test_process_entry_keys(self):
        result = collect_top_processes(count=1)
        if result["top_processes"]:
            p = result["top_processes"][0]
            assert "pid" in p
            assert "name" in p
            assert "cpu_percent" in p


class TestUptimeCollector:
    def test_returns_float(self):
        result = collect_uptime()
        assert isinstance(result, float)

    def test_positive(self):
        result = collect_uptime()
        assert result > 0

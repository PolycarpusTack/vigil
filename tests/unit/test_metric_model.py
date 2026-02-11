"""Unit tests for metric_model table builder.

Tests cover:
- build_metrics_table creates table with expected columns
- build_agents_table creates table with expected columns
- Indexes are created
"""

from sqlalchemy import MetaData

from vigil.storage.metric_model import build_agents_table, build_metrics_table


class TestMetricsTable:
    """Tests for build_metrics_table."""

    def test_metrics_table_columns(self):
        """metrics table has all expected columns."""
        metadata = MetaData()
        table = build_metrics_table(metadata)

        col_names = {c.name for c in table.columns}
        expected = {
            "id",
            "agent_id",
            "hostname",
            "timestamp",
            "cpu_percent",
            "memory_percent",
            "memory_used_mb",
            "memory_total_mb",
            "disk_percent",
            "disk_used_gb",
            "disk_total_gb",
            "network_bytes_sent",
            "network_bytes_recv",
            "uptime_seconds",
            "process_count",
            "metadata_json",
            "created_at",
        }
        assert expected == col_names

    def test_metrics_table_primary_key(self):
        """metrics table has 'id' as primary key."""
        metadata = MetaData()
        table = build_metrics_table(metadata)
        pk_cols = [c.name for c in table.primary_key.columns]
        assert pk_cols == ["id"]

    def test_metrics_table_name(self):
        """Table name is 'metrics'."""
        metadata = MetaData()
        table = build_metrics_table(metadata)
        assert table.name == "metrics"


class TestAgentsTable:
    """Tests for build_agents_table."""

    def test_agents_table_columns(self):
        """agents table has expected columns."""
        metadata = MetaData()
        table = build_agents_table(metadata)

        col_names = {c.name for c in table.columns}
        expected = {"agent_id", "hostname", "first_seen", "last_seen", "status"}
        assert expected == col_names

    def test_agents_table_primary_key(self):
        """agents table has 'agent_id' as primary key."""
        metadata = MetaData()
        table = build_agents_table(metadata)
        pk_cols = [c.name for c in table.primary_key.columns]
        assert pk_cols == ["agent_id"]

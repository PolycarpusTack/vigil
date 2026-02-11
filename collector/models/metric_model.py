"""Metrics database model."""

import sqlalchemy as sa

from collector.models.database import metadata

metrics_table = sa.Table(
    "metrics",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("agent_id", sa.String(255), nullable=False),
    sa.Column("hostname", sa.String(255), nullable=False),
    sa.Column("timestamp", sa.DateTime, nullable=False),
    sa.Column("cpu_percent", sa.Float),
    sa.Column("memory_percent", sa.Float),
    sa.Column("memory_used_mb", sa.Float),
    sa.Column("memory_total_mb", sa.Float),
    sa.Column("disk_percent", sa.Float),
    sa.Column("disk_used_gb", sa.Float),
    sa.Column("disk_total_gb", sa.Float),
    sa.Column("network_bytes_sent", sa.BigInteger),
    sa.Column("network_bytes_recv", sa.BigInteger),
    sa.Column("uptime_seconds", sa.Float),
    sa.Column("process_count", sa.Integer),
    sa.Column("metadata_json", sa.Text),
    sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
)

sa.Index("ix_cm_agent_id", metrics_table.c.agent_id)
sa.Index("ix_cm_timestamp", metrics_table.c.timestamp)
sa.Index("ix_cm_agent_timestamp", metrics_table.c.agent_id, metrics_table.c.timestamp)

"""Metric storage model using SQLAlchemy Core."""

import logging

logger = logging.getLogger(__name__)

try:
    import sqlalchemy as sa
    from sqlalchemy import (
        Column,
        DateTime,
        Float,
        Index,
        Integer,
        MetaData,
        String,
        Table,
        Text,
    )

    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False


def build_metrics_table(metadata: "MetaData") -> "Table":
    """Build the metrics table schema."""
    table = Table(
        "metrics",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("agent_id", String(255), nullable=False),
        Column("hostname", String(255), nullable=False),
        Column("timestamp", DateTime, nullable=False),
        Column("cpu_percent", Float),
        Column("memory_percent", Float),
        Column("memory_used_mb", Float),
        Column("memory_total_mb", Float),
        Column("disk_percent", Float),
        Column("disk_used_gb", Float),
        Column("disk_total_gb", Float),
        Column("network_bytes_sent", sa.BigInteger),
        Column("network_bytes_recv", sa.BigInteger),
        Column("uptime_seconds", Float),
        Column("process_count", Integer),
        Column("metadata_json", Text),
        Column("created_at", DateTime, nullable=False, server_default=sa.func.now()),
    )
    Index("ix_metrics_agent_id", table.c.agent_id)
    Index("ix_metrics_timestamp", table.c.timestamp)
    Index("ix_metrics_agent_timestamp", table.c.agent_id, table.c.timestamp)
    return table


def build_agents_table(metadata: "MetaData") -> "Table":
    """Build the agents registration table."""
    table = Table(
        "agents",
        metadata,
        Column("agent_id", String(255), primary_key=True),
        Column("hostname", String(255), nullable=False),
        Column("first_seen", DateTime, nullable=False),
        Column("last_seen", DateTime, nullable=False),
        Column("status", String(20), nullable=False, server_default="active"),
    )
    return table

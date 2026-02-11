"""Shared table definitions for audit events.

This is the single source of truth for the audit_events table schema.
Both the core SQLStorageBackend and the collector's event_model import from here.
"""

import sqlalchemy as sa
from sqlalchemy import Column, DateTime, Index, MetaData, String, Table, Text


def build_audit_events_table(metadata: MetaData) -> Table:
    """Build the audit_events table schema.

    Args:
        metadata: SQLAlchemy MetaData instance to bind the table to.

    Returns:
        The audit_events Table object with all columns and indexes.
    """
    table = Table(
        "audit_events",
        metadata,
        Column("event_id", String(36), primary_key=True),
        Column("timestamp", DateTime, nullable=False),
        Column("version", String(20), nullable=False, server_default="1.0.0"),
        Column("actor_type", String(50)),
        Column("actor_username", String(255)),
        Column("action_type", String(50)),
        Column("action_category", String(50)),
        Column("action_operation", String(255)),
        Column("result_status", String(20)),
        Column("application", String(255)),
        Column("environment", String(100)),
        Column("event_data", Text, nullable=False),
        Column("created_at", DateTime, nullable=False, server_default=sa.func.now()),
    )
    Index("ix_audit_events_timestamp", table.c.timestamp)
    Index("ix_audit_events_actor_username", table.c.actor_username)
    Index("ix_audit_events_action_category", table.c.action_category)
    Index("ix_audit_events_action_type", table.c.action_type)
    Index("ix_audit_events_result_status", table.c.result_status)
    Index("ix_audit_events_application", table.c.application)
    Index("ix_audit_events_environment", table.c.environment)
    return table

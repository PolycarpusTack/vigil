"""Agent registration database model."""

import sqlalchemy as sa

from collector.models.database import metadata

agents_table = sa.Table(
    "agents",
    metadata,
    sa.Column("agent_id", sa.String(255), primary_key=True),
    sa.Column("hostname", sa.String(255), nullable=False),
    sa.Column("first_seen", sa.DateTime, nullable=False),
    sa.Column("last_seen", sa.DateTime, nullable=False),
    sa.Column("status", sa.String(20), nullable=False, server_default="active"),
)

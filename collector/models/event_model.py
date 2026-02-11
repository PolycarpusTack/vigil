"""Audit event database model."""

from vigil.storage.table_defs import build_audit_events_table
from collector.models.database import metadata

audit_events_table = build_audit_events_table(metadata)

"""Tests for shared audit_events table definition.

Verifies that the shared table builder produces the expected schema and that
both sql_storage and collector event_model use the same source of truth.
"""

import pytest

try:
    import sqlalchemy as sa

    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False

pytestmark = pytest.mark.skipif(not HAS_SQLALCHEMY, reason="sqlalchemy not installed")

from vigil.storage.table_defs import build_audit_events_table  # noqa: E402


class TestSharedTableDefinition:
    """Tests for the shared audit_events table builder."""

    def test_shared_table_columns_match(self):
        """The shared builder produces all expected columns."""
        metadata = sa.MetaData()
        table = build_audit_events_table(metadata)

        expected_columns = {
            "event_id",
            "timestamp",
            "version",
            "actor_type",
            "actor_username",
            "action_type",
            "action_category",
            "action_operation",
            "result_status",
            "application",
            "environment",
            "event_data",
            "created_at",
        }
        actual_columns = {c.name for c in table.columns}
        assert actual_columns == expected_columns

    def test_shared_table_primary_key(self):
        """The primary key is event_id."""
        metadata = sa.MetaData()
        table = build_audit_events_table(metadata)
        pk_cols = [c.name for c in table.primary_key.columns]
        assert pk_cols == ["event_id"]

    def test_shared_table_indexes(self):
        """All expected indexes are created."""
        metadata = sa.MetaData()
        table = build_audit_events_table(metadata)

        index_names = {idx.name for idx in table.indexes}
        expected_indexes = {
            "ix_audit_events_timestamp",
            "ix_audit_events_actor_username",
            "ix_audit_events_action_category",
            "ix_audit_events_action_type",
            "ix_audit_events_result_status",
            "ix_audit_events_application",
            "ix_audit_events_environment",
        }
        assert expected_indexes.issubset(index_names)

    def test_sql_storage_uses_shared_builder(self):
        """SQLStorageBackend imports from the shared table_defs module."""
        import inspect

        from vigil.storage import sql_storage

        source = inspect.getsource(sql_storage)
        assert "from vigil.storage.table_defs import build_audit_events_table" in source

    def test_collector_event_model_uses_shared_builder(self):
        """Collector event_model imports from the shared table_defs module."""
        import inspect

        from collector.models import event_model

        source = inspect.getsource(event_model)
        assert "from vigil.storage.table_defs import build_audit_events_table" in source

    def test_both_produce_same_columns(self, tmp_path):
        """Both sql_storage and collector event_model produce identical column sets."""
        from vigil.storage.sql_storage import SQLStorageBackend
        from collector.models.event_model import audit_events_table as collector_table

        # Create sql_storage table
        db_path = tmp_path / "schema_test.db"
        backend = SQLStorageBackend({"url": f"sqlite:///{db_path}", "echo": False})

        storage_cols = {c.name for c in backend.audit_events.columns}
        collector_cols = {c.name for c in collector_table.columns}

        backend.close()

        assert storage_cols == collector_cols

"""SQL storage backend using SQLAlchemy Core."""

import json
import logging
from typing import Any, Dict, List, Optional

from vigil.core.event import AuditEvent
from vigil.storage.base import StorageBackend
from vigil.storage.table_defs import build_audit_events_table

logger = logging.getLogger(__name__)

try:
    import sqlalchemy as sa
    from sqlalchemy import MetaData, create_engine

    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False


class SQLStorageBackend(StorageBackend):
    """SQL storage backend supporting SQLite and PostgreSQL via SQLAlchemy Core."""

    def __init__(self, config: Dict[str, Any]):
        if not HAS_SQLALCHEMY:
            raise ImportError(
                "sqlalchemy is required for SQL storage. "
                "Install with: pip install vigil[database]"
            )
        super().__init__(config)
        self.url = config.get("url", "sqlite:///audit.db")
        self.echo = config.get("echo", False)

        self.engine = create_engine(self.url, echo=self.echo)
        self.metadata = MetaData()
        self.audit_events = build_audit_events_table(self.metadata)
        self.metadata.create_all(self.engine)

        logger.info(f"SQL storage backend initialized: {self.url}")

    def store(self, event: AuditEvent):
        """Store an audit event in the database."""
        event_dict = event.to_dict()
        event_data_json = json.dumps(event_dict, default=str)

        action = event_dict.get("action", {})
        actor = event_dict.get("actor", {})
        metadata = event_dict.get("metadata", {})

        row = {
            "event_id": event_dict["event_id"],
            "timestamp": event.timestamp,
            "version": event_dict.get("version", "1.0.0"),
            "actor_type": actor.get("type"),
            "actor_username": actor.get("username"),
            "action_type": action.get("type"),
            "action_category": action.get("category"),
            "action_operation": action.get("operation"),
            "result_status": action.get("result", {}).get("status"),
            "application": metadata.get("application"),
            "environment": metadata.get("environment"),
            "event_data": event_data_json,
        }

        with self.engine.begin() as conn:
            conn.execute(self.audit_events.insert().values(**row))

    def query(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Query stored events with optional filters.

        Args:
            filters: dict of column_name -> value for equality filtering
            limit: max results to return
            offset: number of results to skip

        Returns:
            List of event dictionaries
        """
        stmt = (
            sa.select(self.audit_events)
            .order_by(self.audit_events.c.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )

        if filters:
            for col_name, value in filters.items():
                if hasattr(self.audit_events.c, col_name):
                    stmt = stmt.where(getattr(self.audit_events.c, col_name) == value)

        with self.engine.connect() as conn:
            result = conn.execute(stmt)
            rows = []
            for row in result:
                event_data = json.loads(row.event_data)
                rows.append(event_data)
            return rows

    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Get a single event by ID."""
        stmt = sa.select(self.audit_events).where(self.audit_events.c.event_id == event_id)
        with self.engine.connect() as conn:
            row = conn.execute(stmt).first()
            if row:
                return json.loads(row.event_data)
            return None

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count events matching filters."""
        stmt = sa.select(sa.func.count()).select_from(self.audit_events)
        if filters:
            for col_name, value in filters.items():
                if hasattr(self.audit_events.c, col_name):
                    stmt = stmt.where(getattr(self.audit_events.c, col_name) == value)
        with self.engine.connect() as conn:
            return conn.execute(stmt).scalar()

    def close(self):
        """Dispose of the engine connection pool."""
        self.engine.dispose()
        logger.info("SQL storage backend closed")

"""Database engine and session setup."""

import sqlalchemy as sa
from sqlalchemy import MetaData
from sqlalchemy.orm import Session, sessionmaker

metadata = MetaData()

_engine = None
_SessionLocal = None


def init_db(database_url: str) -> sa.engine.Engine:
    """Initialize the database engine and create all tables."""
    global _engine, _SessionLocal

    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    _engine = sa.create_engine(database_url, connect_args=connect_args)
    _SessionLocal = sessionmaker(bind=_engine)

    # Import models to register tables with metadata
    from collector.models.agent_model import agents_table  # noqa: F401
    from collector.models.event_model import audit_events_table  # noqa: F401
    from collector.models.metric_model import metrics_table  # noqa: F401

    metadata.create_all(_engine)
    return _engine


def get_engine() -> sa.engine.Engine:
    """Get the database engine."""
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _engine


def get_session() -> Session:
    """Get a new database session."""
    if _SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _SessionLocal()

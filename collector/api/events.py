"""Audit event API endpoints."""

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from vigil.core.event import AuditEvent
from vigil.processing.sanitizers import PIISanitizer
from collector.auth.api_keys import verify_api_key
from collector.models.database import get_engine
from collector.models.event_model import audit_events_table

logger = logging.getLogger(__name__)
router = APIRouter(tags=["events"])

# Module-level sanitizer instance for PII processing
_sanitizer = PIISanitizer()


# --- Pydantic Models ---


class ResourceModel(BaseModel):
    """Resource targeted by the action."""

    type: Optional[str] = Field(None, description="Resource type (table, file, endpoint)")
    id: Optional[str] = Field(None, description="Resource identifier")
    name: Optional[str] = Field(None, description="Human-readable resource name")
    path: Optional[str] = Field(None, description="Resource path or URL")


class ResultModel(BaseModel):
    """Outcome of the action."""

    status: str = Field("SUCCESS", description="Result status (SUCCESS, FAILURE)")
    code: Optional[str] = Field(None, description="Application-specific result code")
    message: Optional[str] = Field(None, description="Human-readable result message")
    rows_affected: Optional[int] = Field(None, description="Number of rows affected")
    data_size_bytes: Optional[int] = Field(None, description="Response payload size")


class ActionModel(BaseModel):
    """Describes what happened."""

    type: str = Field("EXECUTE", description="Action type (READ, WRITE, EXECUTE, etc.)")
    category: str = Field("SYSTEM", description="Action category (DATABASE, API, AUTH, etc.)")
    operation: Optional[str] = Field(None, description="Specific operation name")
    description: Optional[str] = Field(None, description="Human-readable description")
    resource: Optional[ResourceModel] = None
    parameters: Optional[dict] = Field(None, description="Operation parameters")
    result: Optional[ResultModel] = None


class ActorModel(BaseModel):
    """Who performed the action."""

    type: str = Field("anonymous", description="Actor type (user, service, system)")
    id: Optional[str] = Field(None, description="Actor identifier")
    username: Optional[str] = Field(None, description="Actor username")
    email: Optional[str] = Field(None, description="Actor email (will be redacted)")
    roles: Optional[List[str]] = Field(None, description="Actor roles")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent string")


class SessionModel(BaseModel):
    """Request/session correlation identifiers."""

    session_id: Optional[str] = None
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None


class PerformanceModel(BaseModel):
    """Performance metrics for the action."""

    duration_ms: Optional[float] = Field(None, description="Action duration in milliseconds")
    cpu_time_ms: Optional[float] = None
    memory_mb: Optional[float] = None
    slow_query: Optional[bool] = False
    threshold_exceeded: Optional[bool] = False


class ErrorModel(BaseModel):
    """Error information if the action failed."""

    occurred: Optional[bool] = False
    type: Optional[str] = Field(None, description="Exception type name")
    message: Optional[str] = Field(None, description="Error message")
    stack_trace: Optional[str] = Field(None, description="Stack trace (redacted in response)")
    handled: Optional[bool] = True


class AuditEventRequest(BaseModel):
    """A single audit event to ingest."""

    event_id: Optional[str] = Field(
        default_factory=lambda: str(uuid4()), description="Unique event ID (auto-generated)"
    )
    timestamp: Optional[str] = Field(None, description="ISO 8601 timestamp (auto-generated)")
    version: str = Field("1.0.0", description="Event schema version")
    session: Optional[SessionModel] = None
    actor: Optional[ActorModel] = None
    action: ActionModel = Field(..., description="Required: what happened")
    performance: Optional[PerformanceModel] = None
    error: Optional[ErrorModel] = None
    system: Optional[dict] = None
    custom: Optional[dict] = None
    metadata: Optional[dict] = Field(None, description="Application and environment metadata")


class BatchEventRequest(BaseModel):
    """Batch of audit events to ingest (max 100)."""

    events: List[AuditEventRequest] = Field(..., max_length=100)


# --- Helpers ---


def _sanitize_event_dict(event_dict: dict) -> dict:
    """Run event dict through PII sanitizer via AuditEvent round-trip."""
    try:
        event = AuditEvent.from_dict(event_dict.copy())
        sanitized = _sanitizer.sanitize_event(event)
        return sanitized.to_dict()
    except Exception as e:
        logger.warning(f"PII sanitization failed, storing original event: {e}")
        return event_dict


def _store_event(engine, event_dict: dict):
    """Insert a single event dict into the database after PII sanitization."""
    event_dict = _sanitize_event_dict(event_dict)

    action = event_dict.get("action", {})
    actor = event_dict.get("actor", {})
    meta = event_dict.get("metadata", {})

    ts = event_dict.get("timestamp")
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)
    elif ts is None:
        ts = datetime.now(timezone.utc)

    row = {
        "event_id": event_dict.get("event_id", str(uuid4())),
        "timestamp": ts,
        "version": event_dict.get("version", "1.0.0"),
        "actor_type": actor.get("type"),
        "actor_username": actor.get("username"),
        "action_type": action.get("type"),
        "action_category": action.get("category"),
        "action_operation": action.get("operation"),
        "result_status": action.get("result", {}).get("status") if action.get("result") else None,
        "application": meta.get("application"),
        "environment": meta.get("environment"),
        "event_data": json.dumps(event_dict, default=str),
    }
    with engine.begin() as conn:
        conn.execute(audit_events_table.insert().values(**row))
    return row["event_id"]


# --- Endpoints ---


@router.post("/api/v1/events", status_code=201)
def ingest_event(event: AuditEventRequest, _key: str = Depends(verify_api_key)):
    """Ingest a single audit event."""
    engine = get_engine()
    event_dict = event.model_dump(exclude_none=True)
    if event_dict.get("timestamp") is None:
        event_dict["timestamp"] = datetime.now(timezone.utc).isoformat()

    event_id = _store_event(engine, event_dict)
    return {"status": "accepted", "event_id": event_id}


@router.post("/api/v1/events/batch", status_code=201)
def ingest_batch(batch: BatchEventRequest, _key: str = Depends(verify_api_key)):
    """Ingest a batch of audit events (up to 100)."""
    engine = get_engine()
    accepted = []
    errors = []

    for i, event in enumerate(batch.events):
        try:
            event_dict = event.model_dump(exclude_none=True)
            if event_dict.get("timestamp") is None:
                event_dict["timestamp"] = datetime.now(timezone.utc).isoformat()
            eid = _store_event(engine, event_dict)
            accepted.append(eid)
        except Exception as e:
            errors.append({"index": i, "error": str(e)})

    return {
        "status": "accepted",
        "accepted": len(accepted),
        "errors": errors,
        "event_ids": accepted,
    }


@router.get("/api/v1/events")
def query_events(
    action_category: Optional[str] = Query(None),
    action_type: Optional[str] = Query(None),
    actor_username: Optional[str] = Query(None),
    application: Optional[str] = Query(None),
    environment: Optional[str] = Query(None),
    result_status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _key: str = Depends(verify_api_key),
):
    """Query stored audit events with filtering and pagination."""
    engine = get_engine()
    stmt = (
        sa.select(audit_events_table)
        .order_by(audit_events_table.c.timestamp.desc())
        .limit(limit)
        .offset(offset)
    )

    filters = {
        "action_category": action_category,
        "action_type": action_type,
        "actor_username": actor_username,
        "application": application,
        "environment": environment,
        "result_status": result_status,
    }
    for col_name, value in filters.items():
        if value is not None:
            stmt = stmt.where(getattr(audit_events_table.c, col_name) == value)

    # Count query
    count_stmt = sa.select(sa.func.count()).select_from(audit_events_table)
    for col_name, value in filters.items():
        if value is not None:
            count_stmt = count_stmt.where(getattr(audit_events_table.c, col_name) == value)

    with engine.connect() as conn:
        total = conn.execute(count_stmt).scalar()
        rows = conn.execute(stmt).fetchall()

    events = [json.loads(row.event_data) for row in rows]
    return {"total": total, "limit": limit, "offset": offset, "events": events}


@router.get("/api/v1/events/{event_id}")
def get_event(event_id: str, _key: str = Depends(verify_api_key)):
    """Get a single audit event by ID."""
    engine = get_engine()
    stmt = sa.select(audit_events_table).where(audit_events_table.c.event_id == event_id)
    with engine.connect() as conn:
        row = conn.execute(stmt).first()

    if not row:
        raise HTTPException(status_code=404, detail="Event not found")

    return json.loads(row.event_data)

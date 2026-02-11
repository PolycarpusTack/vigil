"""Metrics API endpoints."""

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from collector.auth.api_keys import verify_api_key
from collector.models.agent_model import agents_table
from collector.models.database import get_engine
from collector.models.metric_model import metrics_table

logger = logging.getLogger(__name__)
router = APIRouter(tags=["metrics"])


# --- Pydantic Models ---


class TopProcess(BaseModel):
    """A single process entry from the agent's top-N list."""

    pid: int
    name: str
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    memory_mb: Optional[float] = None


class MetricsPayload(BaseModel):
    """System metrics collected by a monitoring agent."""

    cpu_percent: float
    memory_percent: float
    memory_used_mb: Optional[float] = None
    memory_total_mb: Optional[float] = None
    disk_percent: Optional[float] = None
    disk_used_gb: Optional[float] = None
    disk_total_gb: Optional[float] = None
    network_bytes_sent: Optional[int] = None
    network_bytes_recv: Optional[int] = None
    uptime_seconds: Optional[float] = None
    process_count: Optional[int] = None
    top_processes: Optional[List[TopProcess]] = None


class MetricEventRequest(BaseModel):
    """A metric event submitted by a monitoring agent."""

    agent_id: str
    hostname: str
    timestamp: Optional[str] = None
    metrics: MetricsPayload


# --- Helpers ---


def _upsert_agent(engine, agent_id: str, hostname: str, now: datetime):
    """Insert or update agent last_seen."""
    with engine.begin() as conn:
        existing = conn.execute(
            sa.select(agents_table).where(agents_table.c.agent_id == agent_id)
        ).first()

        if existing:
            conn.execute(
                agents_table.update()
                .where(agents_table.c.agent_id == agent_id)
                .values(last_seen=now, hostname=hostname)
            )
        else:
            conn.execute(
                agents_table.insert().values(
                    agent_id=agent_id,
                    hostname=hostname,
                    first_seen=now,
                    last_seen=now,
                    status="active",
                )
            )


# --- Endpoints ---


@router.post("/api/v1/metrics", status_code=201)
def ingest_metrics(payload: MetricEventRequest, _key: str = Depends(verify_api_key)):
    """Ingest server agent metrics."""
    engine = get_engine()

    ts = payload.timestamp
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)
    elif ts is None:
        ts = datetime.now(timezone.utc)

    m = payload.metrics

    # Store top_processes in metadata_json
    meta = {}
    if m.top_processes:
        meta["top_processes"] = [p.model_dump() for p in m.top_processes]

    row = {
        "agent_id": payload.agent_id,
        "hostname": payload.hostname,
        "timestamp": ts,
        "cpu_percent": m.cpu_percent,
        "memory_percent": m.memory_percent,
        "memory_used_mb": m.memory_used_mb,
        "memory_total_mb": m.memory_total_mb,
        "disk_percent": m.disk_percent,
        "disk_used_gb": m.disk_used_gb,
        "disk_total_gb": m.disk_total_gb,
        "network_bytes_sent": m.network_bytes_sent,
        "network_bytes_recv": m.network_bytes_recv,
        "uptime_seconds": m.uptime_seconds,
        "process_count": m.process_count,
        "metadata_json": json.dumps(meta) if meta else None,
    }

    with engine.begin() as conn:
        conn.execute(metrics_table.insert().values(**row))

    _upsert_agent(engine, payload.agent_id, payload.hostname, ts)

    return {"status": "accepted", "agent_id": payload.agent_id}


@router.get("/api/v1/metrics/{agent_id}")
def query_metrics(
    agent_id: str,
    start: Optional[str] = Query(None, description="Start time (ISO 8601)"),
    end: Optional[str] = Query(None, description="End time (ISO 8601)"),
    limit: int = Query(100, ge=1, le=1000),
    _key: str = Depends(verify_api_key),
):
    """Query metrics for a specific agent with optional time range."""
    engine = get_engine()

    stmt = (
        sa.select(metrics_table)
        .where(metrics_table.c.agent_id == agent_id)
        .order_by(metrics_table.c.timestamp.desc())
        .limit(limit)
    )

    if start:
        stmt = stmt.where(metrics_table.c.timestamp >= datetime.fromisoformat(start))
    if end:
        stmt = stmt.where(metrics_table.c.timestamp <= datetime.fromisoformat(end))

    with engine.connect() as conn:
        rows = conn.execute(stmt).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail=f"No metrics found for agent: {agent_id}")

    results = []
    for row in rows:
        entry = {
            "agent_id": row.agent_id,
            "hostname": row.hostname,
            "timestamp": row.timestamp.isoformat(),
            "metrics": {
                "cpu_percent": row.cpu_percent,
                "memory_percent": row.memory_percent,
                "memory_used_mb": row.memory_used_mb,
                "memory_total_mb": row.memory_total_mb,
                "disk_percent": row.disk_percent,
                "disk_used_gb": row.disk_used_gb,
                "disk_total_gb": row.disk_total_gb,
                "network_bytes_sent": row.network_bytes_sent,
                "network_bytes_recv": row.network_bytes_recv,
                "uptime_seconds": row.uptime_seconds,
                "process_count": row.process_count,
            },
        }
        if row.metadata_json:
            meta = json.loads(row.metadata_json)
            if "top_processes" in meta:
                entry["metrics"]["top_processes"] = meta["top_processes"]
        results.append(entry)

    return {"agent_id": agent_id, "count": len(results), "metrics": results}

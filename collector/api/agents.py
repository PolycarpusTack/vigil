"""Agent registration endpoints."""

import sqlalchemy as sa
from fastapi import APIRouter, Depends

from collector.auth.api_keys import verify_api_key
from collector.models.agent_model import agents_table
from collector.models.database import get_engine

router = APIRouter(tags=["agents"])


@router.get("/api/v1/agents")
def list_agents(_key: str = Depends(verify_api_key)):
    """List all registered agents."""
    engine = get_engine()
    stmt = sa.select(agents_table).order_by(agents_table.c.last_seen.desc())

    with engine.connect() as conn:
        rows = conn.execute(stmt).fetchall()

    agents = [
        {
            "agent_id": row.agent_id,
            "hostname": row.hostname,
            "first_seen": row.first_seen.isoformat(),
            "last_seen": row.last_seen.isoformat(),
            "status": row.status,
        }
        for row in rows
    ]

    return {"count": len(agents), "agents": agents}

"""Health check endpoints."""

from fastapi import APIRouter
from sqlalchemy import text as sa_text

from collector.models.database import get_engine

router = APIRouter(tags=["health"])


@router.get("/api/v1/health")
def health():
    """Basic health check."""
    return {"status": "ok"}


@router.get("/api/v1/ready")
def ready():
    """Readiness check - verifies database connectivity."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(sa_text("SELECT 1"))
        return {"status": "ready", "database": "ok"}
    except Exception as e:
        return {"status": "not_ready", "database": str(e)}

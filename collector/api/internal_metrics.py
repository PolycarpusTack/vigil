"""Internal metrics endpoint for collector observability."""

from fastapi import APIRouter, Request

router = APIRouter(tags=["internal"])


@router.get("/api/v1/internal/metrics")
def internal_metrics(request: Request):
    """Return collector internal metrics (no auth required)."""
    tracker = request.state.metrics_tracker
    return tracker.get_metrics()

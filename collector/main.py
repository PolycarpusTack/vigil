"""Collector service FastAPI application."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from collector.api import agents, events, health, internal_metrics, metrics
from collector.auth.api_keys import configure_api_keys
from collector.config import get_config
from collector.logging_config import configure_logging
from collector.middleware.metrics_tracker import MetricsTrackerMiddleware
from collector.middleware.rate_limit import RateLimitMiddleware
from collector.models.database import init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: init DB and auth on startup."""
    config = get_config()

    configure_logging(level=config.log_level, log_format=config.log_format)
    logger.info(f"Starting collector service on {config.bind_host}:{config.bind_port}")

    # Initialize database
    init_db(config.database_url)
    logger.info(f"Database initialized: {config.database_url}")

    # Configure API key auth
    configure_api_keys(config.api_keys)

    yield

    logger.info("Collector service shutting down")


app = FastAPI(
    title="Vigil Collector",
    description=(
        "Central collector service for audit events and server metrics. "
        "Provides event ingestion, querying, batch processing, agent metrics, "
        "and internal observability endpoints."
    ),
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "health", "description": "Health and readiness checks"},
        {"name": "events", "description": "Audit event ingestion and querying"},
        {"name": "metrics", "description": "Server agent metric ingestion and querying"},
        {"name": "agents", "description": "Registered agent management"},
        {"name": "internal", "description": "Internal observability (no auth required)"},
    ],
)

# CORS middleware — must be added before other middleware
_cors_config = get_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_config.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

# Metrics tracking middleware
app.add_middleware(MetricsTrackerMiddleware)

# Rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Register routers
app.include_router(health.router)
app.include_router(events.router)
app.include_router(metrics.router)
app.include_router(agents.router)
app.include_router(internal_metrics.router)


if __name__ == "__main__":
    import uvicorn

    config = get_config()
    uvicorn.run(
        "collector.main:app",
        host=config.bind_host,
        port=config.bind_port,
        reload=True,
    )

"""Collector service configuration."""

import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class CollectorConfig:
    """Configuration for the collector service."""

    database_url: str = os.environ.get("DATABASE_URL", "sqlite:///audit_collector.db")
    bind_host: str = os.environ.get("BIND_HOST", "0.0.0.0")
    bind_port: int = int(os.environ.get("BIND_PORT", "8080"))
    api_keys: List[str] = field(default_factory=lambda: _load_api_keys())
    log_level: str = os.environ.get("LOG_LEVEL", "INFO")
    log_format: str = os.environ.get("LOG_FORMAT", "text")
    max_batch_size: int = int(os.environ.get("MAX_BATCH_SIZE", "100"))
    cors_origins: List[str] = field(default_factory=lambda: _load_cors_origins())


def _load_api_keys() -> List[str]:
    """Load API keys from environment or default."""
    keys_str = os.environ.get("API_KEYS", "")
    if keys_str:
        return [k.strip() for k in keys_str.split(",") if k.strip()]
    return []


def _load_cors_origins() -> List[str]:
    """Load CORS allowed origins from environment or default to localhost."""
    origins_str = os.environ.get("CORS_ORIGINS", "")
    if origins_str:
        return [o.strip() for o in origins_str.split(",") if o.strip()]
    return ["http://localhost:3000", "http://localhost:8080"]


def get_config() -> CollectorConfig:
    """Get collector configuration singleton."""
    return CollectorConfig()

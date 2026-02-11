"""Agent health status tracking."""

import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

DEGRADED_THRESHOLD = 3


class HealthTracker:
    """Tracks agent health status across collection cycles.

    Args:
        agent_id: Identifier for this agent instance.
    """

    def __init__(self, agent_id: str) -> None:
        self._agent_id = agent_id
        self._start_time = time.monotonic()
        self._last_collection_time: Optional[str] = None
        self._last_send_success: Optional[bool] = None
        self._consecutive_failures: int = 0

    def record_success(self) -> None:
        """Record a successful metric send."""
        self._last_collection_time = datetime.now(timezone.utc).isoformat()
        self._last_send_success = True
        self._consecutive_failures = 0

    def record_failure(self) -> None:
        """Record a failed metric send."""
        self._last_collection_time = datetime.now(timezone.utc).isoformat()
        self._last_send_success = False
        self._consecutive_failures += 1

    def get_status(self) -> Dict[str, Any]:
        """Return current health status as a dictionary."""
        uptime = time.monotonic() - self._start_time
        status = "healthy" if self._consecutive_failures <= DEGRADED_THRESHOLD else "degraded"

        return {
            "agent_id": self._agent_id,
            "status": status,
            "uptime_seconds": round(uptime, 2),
            "last_collection_time": self._last_collection_time,
            "last_send_success": self._last_send_success,
            "consecutive_failures": self._consecutive_failures,
        }

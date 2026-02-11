"""Middleware that tracks request counts and errors for internal metrics."""

import time
from typing import Any, Dict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class MetricsTrackerMiddleware(BaseHTTPMiddleware):
    """Tracks request_count, error_count, and service uptime."""

    def __init__(self, app: Any) -> None:
        super().__init__(app)
        self._start_time = time.monotonic()
        self._request_count = 0
        self._error_count = 0

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip counting the internal metrics endpoint itself
        if request.url.path == "/api/v1/internal/metrics":
            # Attach tracker to request state so endpoint can read it
            request.state.metrics_tracker = self
            return await call_next(request)

        self._request_count += 1
        try:
            response = await call_next(request)
            if response.status_code >= 500:
                self._error_count += 1
            return response
        except Exception:
            self._error_count += 1
            raise

    def get_metrics(self) -> Dict[str, Any]:
        """Return current metrics snapshot."""
        uptime = time.monotonic() - self._start_time
        return {
            "request_count": self._request_count,
            "error_count": self._error_count,
            "uptime_seconds": round(uptime, 2),
        }

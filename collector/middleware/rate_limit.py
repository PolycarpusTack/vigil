"""Rate limiting middleware for the collector service."""

import logging
import os
import time
from collections import defaultdict
from typing import Dict, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# Defaults: 100 requests per 60 seconds per client
DEFAULT_RATE_LIMIT = int(os.environ.get("RATE_LIMIT_REQUESTS", "100"))
DEFAULT_RATE_WINDOW = int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "60"))


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory sliding-window rate limiter keyed by client IP."""

    def __init__(
        self,
        app,
        max_requests: int = DEFAULT_RATE_LIMIT,
        window_seconds: int = DEFAULT_RATE_WINDOW,
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # client_key -> list of request timestamps
        self._requests: Dict[str, list] = defaultdict(list)

    def _get_client_key(self, request: Request) -> str:
        """Extract client identifier from request."""
        # Use X-Forwarded-For if behind a proxy, otherwise use client host
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _is_rate_limited(self, client_key: str) -> Tuple[bool, int]:
        """Check if client has exceeded rate limit.

        Returns:
            Tuple of (is_limited, remaining_requests)
        """
        now = time.monotonic()
        window_start = now - self.window_seconds

        # Remove expired entries
        timestamps = self._requests[client_key]
        self._requests[client_key] = [t for t in timestamps if t > window_start]

        current_count = len(self._requests[client_key])
        remaining = max(0, self.max_requests - current_count)

        if current_count >= self.max_requests:
            return True, 0

        return False, remaining

    async def dispatch(self, request: Request, call_next):
        """Process request through rate limiter."""
        # Skip rate limiting for health checks
        if request.url.path in ("/api/v1/health", "/api/v1/ready"):
            return await call_next(request)

        client_key = self._get_client_key(request)
        is_limited, remaining = self._is_rate_limited(client_key)

        if is_limited:
            logger.warning(f"Rate limit exceeded for client {client_key}")
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Try again later.",
                    "retry_after_seconds": self.window_seconds,
                },
                headers={"Retry-After": str(self.window_seconds)},
            )

        # Record this request
        self._requests[client_key].append(time.monotonic())

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining - 1)
        return response

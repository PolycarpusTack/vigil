"""HTTP transport for sending metrics to the collector."""

import logging
import time
from typing import Any, Dict

import requests

logger = logging.getLogger(__name__)

DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_BASE = 1.0  # seconds


class HTTPSender:
    """Sends metric payloads to the collector via HTTP POST with retry."""

    def __init__(
        self,
        collector_url: str,
        api_key: str,
        timeout: int = 10,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_base: float = DEFAULT_BACKOFF_BASE,
    ):
        self.base_url = collector_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.session = requests.Session()
        if api_key:
            self.session.headers["Authorization"] = f"Bearer {api_key}"
        self.session.headers["Content-Type"] = "application/json"

    def send_metrics(self, payload: Dict[str, Any]) -> bool:
        """POST metrics to the collector with exponential backoff retry.

        Args:
            payload: Metric event dict matching metric_event.schema.json

        Returns:
            True if accepted, False if all attempts failed
        """
        url = f"{self.base_url}/api/v1/metrics"

        for attempt in range(self.max_retries):
            try:
                resp = self.session.post(url, json=payload, timeout=self.timeout)
                if resp.status_code == 201:
                    logger.debug(f"Metrics accepted by collector: {resp.json()}")
                    return True

                # 4xx errors (except 429) are not retryable
                if 400 <= resp.status_code < 500 and resp.status_code != 429:
                    logger.warning(f"Collector returned {resp.status_code}: {resp.text}")
                    return False

                # 5xx or 429 — retryable
                logger.warning(
                    f"Collector returned {resp.status_code} on attempt "
                    f"{attempt + 1}/{self.max_retries}"
                )

            except requests.ConnectionError:
                logger.error(
                    f"Cannot connect to collector at {url} "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )
            except requests.Timeout:
                logger.error(
                    f"Timeout sending metrics to {url} "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )
            except Exception as e:
                logger.error(f"Unexpected error sending metrics: {e}")
                return False

            # Exponential backoff before retry (skip sleep on last attempt)
            if attempt < self.max_retries - 1:
                delay = self.backoff_base * (2**attempt)
                logger.debug(f"Retrying in {delay:.1f}s...")
                time.sleep(delay)

        logger.error(f"All {self.max_retries} attempts failed for {url}")
        return False

    def close(self):
        """Close the HTTP session."""
        self.session.close()

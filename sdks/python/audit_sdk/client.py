"""Python SDK client for the Vigil collector."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

import requests

logger = logging.getLogger(__name__)


class AuditClient:
    """Client for sending audit events to the collector service.

    Usage:
        client = AuditClient("http://localhost:8080", api_key="my-key")
        client.log(
            action_type="READ",
            action_category="DATABASE",
            operation="query_users",
            actor={"type": "user", "username": "admin"},
        )
    """

    def __init__(
        self,
        collector_url: str,
        api_key: str = "",
        timeout: int = 10,
        application: str = "",
        environment: str = "",
    ):
        self.base_url = collector_url.rstrip("/")
        self.timeout = timeout
        self.application = application
        self.environment = environment

        self.session = requests.Session()
        self.session.headers["Content-Type"] = "application/json"
        if api_key:
            self.session.headers["Authorization"] = f"Bearer {api_key}"

    def log(
        self,
        action_type: str = "EXECUTE",
        action_category: str = "SYSTEM",
        operation: str = "",
        actor: Optional[Dict[str, Any]] = None,
        resource: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        performance: Optional[Dict[str, Any]] = None,
        error: Optional[Dict[str, Any]] = None,
        custom: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        event_id: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a single audit event to the collector.

        Returns:
            Response dict from the collector
        """
        event = self._build_event(
            action_type=action_type,
            action_category=action_category,
            operation=operation,
            actor=actor,
            resource=resource,
            result=result,
            parameters=parameters,
            performance=performance,
            error=error,
            custom=custom,
            metadata=metadata,
            event_id=event_id,
            timestamp=timestamp,
        )

        resp = self.session.post(
            f"{self.base_url}/api/v1/events",
            json=event,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def log_batch(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Send a batch of audit events to the collector.

        Args:
            events: List of event dicts (each matching audit_event schema)

        Returns:
            Response dict from the collector
        """
        # Ensure each event has an event_id and timestamp
        for event in events:
            if "event_id" not in event:
                event["event_id"] = str(uuid4())
            if "timestamp" not in event:
                event["timestamp"] = datetime.now(timezone.utc).isoformat()

        resp = self.session.post(
            f"{self.base_url}/api/v1/events/batch",
            json={"events": events},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def log_audit_event(self, audit_event) -> Dict[str, Any]:
        """Send an existing AuditEvent object from vigil to the collector.

        Args:
            audit_event: An vigil.core.event.AuditEvent instance

        Returns:
            Response dict from the collector
        """
        event_dict = audit_event.to_dict()
        resp = self.session.post(
            f"{self.base_url}/api/v1/events",
            json=event_dict,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def _build_event(self, **kwargs) -> Dict[str, Any]:
        """Build an event dict from keyword arguments."""
        event = {
            "event_id": kwargs.get("event_id") or str(uuid4()),
            "timestamp": kwargs.get("timestamp") or datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0",
            "action": {
                "type": kwargs.get("action_type", "EXECUTE"),
                "category": kwargs.get("action_category", "SYSTEM"),
            },
        }

        if kwargs.get("operation"):
            event["action"]["operation"] = kwargs["operation"]
        if kwargs.get("resource"):
            event["action"]["resource"] = kwargs["resource"]
        if kwargs.get("result"):
            event["action"]["result"] = kwargs["result"]
        if kwargs.get("parameters"):
            event["action"]["parameters"] = kwargs["parameters"]
        if kwargs.get("actor"):
            event["actor"] = kwargs["actor"]
        if kwargs.get("performance"):
            event["performance"] = kwargs["performance"]
        if kwargs.get("error"):
            event["error"] = kwargs["error"]
        if kwargs.get("custom"):
            event["custom"] = kwargs["custom"]

        meta = kwargs.get("metadata") or {}
        if self.application:
            meta.setdefault("application", self.application)
        if self.environment:
            meta.setdefault("environment", self.environment)
        if meta:
            event["metadata"] = meta

        return event

    def close(self):
        """Close the underlying HTTP session."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

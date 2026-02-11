#!/usr/bin/env python3
"""Prototype app demonstrating Vigil options and features.

Run:
  python examples/prototype_app.py
  python examples/prototype_app.py --config examples/prototype_config.yaml
"""

import argparse
import time
from pathlib import Path
from typing import List

from vigil import AuditContext, AuditEngine, audit_log
from vigil.core.event import AuditEvent
from vigil.storage.base import StorageBackend


class InMemoryBackend(StorageBackend):
    """Simple in-memory backend to show custom backend integration."""

    def __init__(self):
        super().__init__({"enabled": True})
        self.events: List[AuditEvent] = []

    def store(self, event: AuditEvent):
        self.events.append(event)

    def __repr__(self) -> str:
        return f"InMemoryBackend(events={len(self.events)})"


def parse_args():
    parser = argparse.ArgumentParser(description="Vigil Prototype")
    parser.add_argument(
        "--config",
        default=None,
        help="Optional path to YAML config file",
    )
    parser.add_argument(
        "--no-sanitize",
        action="store_true",
        help="Disable PII sanitization",
    )
    parser.add_argument(
        "--capture-result",
        action="store_true",
        help="Capture return values in decorator logs",
    )
    parser.add_argument(
        "--format",
        choices=["json", "jsonl", "csv", "text"],
        default=None,
        help="Override file backend format",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 80)
    print("Vigil - Prototype App")
    print("=" * 80)

    # Initialize engine (config file optional)
    if args.config:
        config_path = Path(args.config)
        audit = AuditEngine(config_file=str(config_path))
    else:
        audit = AuditEngine()

    # Add a custom in-memory backend to show extensibility
    memory_backend = InMemoryBackend()
    audit.storage_backends.append(memory_backend)

    # Apply runtime configuration overrides
    if args.no_sanitize:
        audit.sanitizer = None
    if args.format:
        for backend in audit.storage_backends:
            if hasattr(backend, "format"):
                backend.format = args.format

    print(f"\nEngine: {audit}")
    print(f"Backends: {[b.__class__.__name__ for b in audit.storage_backends]}")

    # Direct API logging
    direct_event = audit.log(
        action="user_login",
        category="AUTH",
        action_type="LOGIN",
        actor={"username": "alice", "ip_address": "203.0.113.5"},
        parameters={"method": "password"},
        result={"status": "SUCCESS"},
        performance={"duration_ms": 120},
        metadata={"request_id": "req-123"},
    )

    # Decorator-based logging with parameter capture
    @audit_log(
        category="DATABASE",
        action_type="READ",
        capture_params=True,
        capture_result=args.capture_result,
    )
    def fetch_account(account_id: str):
        time.sleep(0.05)
        return {"id": account_id, "balance": 50}

    fetch_account("acct_001")

    # Context manager logging with error capture
    try:
        with AuditContext(
            action="PAYMENT",
            category="SYSTEM",
            action_type="EXECUTE",
            actor={"username": "alice"},
            capture_exceptions=True,
        ):
            time.sleep(0.02)
            raise ValueError("charge failed for user alice@example.com")
    except ValueError:
        pass

    # PII sanitization example
    pii_event = audit.log(
        action="user_registration",
        category="AUTH",
        action_type="CREATE",
        actor={"username": "bob", "email": "bob@example.com"},
        parameters={
            "email": "bob@example.com",
            "password": "SuperSecret123",
            "credit_card": "4532-1234-5678-9010",
            "ssn": "123-45-6789",
        },
    )

    # Minimal "integration-style" example: pretend HTTP request handler
    def handle_request(method: str, path: str, user: str):
        with AuditContext(
            action="HTTP_REQUEST",
            category="API",
            action_type="EXECUTE",
            actor={"username": user, "ip_address": "198.51.100.9"},
            resource_type="endpoint",
            resource_name=path,
        ):
            time.sleep(0.01)
            return {"status": 200, "method": method, "path": path}

    handle_request("GET", "/v1/accounts", "api_user")

    # Show stats and in-memory backend summary
    print("\nStats:", audit.get_stats())
    print("In-memory events:", len(memory_backend.events))
    if memory_backend.events:
        print("Last event summary:")
        last = memory_backend.events[-1].to_dict()
        print(
            f"  action={last['action'].get('operation')} "
            f"status={last['action'].get('result', {}).get('status')}"
        )

    # Print a sanitized event preview
    if pii_event:
        print("\nSanitized event preview (user_registration):")
        preview = pii_event.to_dict()
        print(f"  actor.email={preview['actor'].get('email')}")
        print(f"  parameters.email={preview['action'].get('parameters', {}).get('email')}")
        print(f"  parameters.password={preview['action'].get('parameters', {}).get('password')}")
        print(f"  parameters.credit_card={preview['action'].get('parameters', {}).get('credit_card')}")

    print("\nLog files: ./logs/audit/ (default)")
    print("Prototype completed.")


if __name__ == "__main__":
    main()

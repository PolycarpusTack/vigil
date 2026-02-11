"""Pytest configuration and shared fixtures for Vigil tests."""

import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator

import pytest

from vigil.core.engine import AuditEngine
from vigil.core.event import ActionContext, ActorContext, AuditEvent
from vigil.utils.config import AuditConfig


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files.

    Yields:
        Path to temporary directory

    Cleanup:
        Removes directory and all contents after test
    """
    temp_path = Path(tempfile.mkdtemp(prefix="audit_test_"))
    try:
        yield temp_path
    finally:
        # Cleanup: remove directory and all contents
        if temp_path.exists():
            shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def audit_log_dir(temp_dir: Path) -> Path:
    """Create directory for audit logs.

    Args:
        temp_dir: Temporary directory fixture

    Returns:
        Path to audit log directory
    """
    log_dir = temp_dir / "logs" / "audit"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


@pytest.fixture
def basic_config(audit_log_dir: Path) -> Dict[str, Any]:
    """Create basic audit configuration.

    Args:
        audit_log_dir: Audit log directory fixture

    Returns:
        Configuration dictionary
    """
    return {
        "vigil": {
            "core": {
                "enabled": True,
                "application_name": "test_app",
                "environment": "test",
            },
            "storage": {
                "backends": [
                    {
                        "type": "file",
                        "enabled": True,
                        "directory": str(audit_log_dir),
                        "format": "json",
                    }
                ]
            },
            "processing": {"sanitization": {"enabled": True}},
        }
    }


@pytest.fixture
def audit_config(basic_config: Dict[str, Any]) -> AuditConfig:
    """Create AuditConfig instance.

    Args:
        basic_config: Basic configuration dictionary

    Returns:
        AuditConfig instance
    """
    return AuditConfig(config_dict=basic_config)


@pytest.fixture
def audit_engine(audit_config: AuditConfig) -> Generator[AuditEngine, None, None]:
    """Create AuditEngine instance.

    Args:
        audit_config: Audit configuration fixture

    Yields:
        AuditEngine instance

    Cleanup:
        Shuts down engine after test
    """
    engine = AuditEngine(config=audit_config)
    try:
        yield engine
    finally:
        engine.shutdown()


@pytest.fixture
def sample_event() -> AuditEvent:
    """Create a sample audit event for testing.

    Returns:
        Sample AuditEvent instance
    """
    event = AuditEvent()
    event.actor = ActorContext(
        type="user",
        id="user123",
        username="testuser",
        email="test@example.com",
        roles=["admin"],
        ip_address="192.168.1.100",
    )
    event.action = ActionContext(
        type="READ",
        category="DATABASE",
        operation="query_execution",
        parameters={"query": "SELECT * FROM users WHERE id = ?", "params": [123]},
    )
    event.action.result.status = "SUCCESS"
    event.performance.duration_ms = 45.6
    return event


@pytest.fixture
def sample_event_dict() -> Dict[str, Any]:
    """Create a sample event dictionary for testing.

    Returns:
        Sample event dictionary
    """
    return {
        "event_id": "test-event-123",
        "timestamp": "2024-01-15T10:30:00",
        "version": "1.0.0",
        "session": {
            "session_id": "session-123",
            "request_id": "req-456",
        },
        "actor": {
            "type": "user",
            "id": "user-789",
            "username": "testuser",
            "email": "test@example.com",
        },
        "action": {
            "type": "READ",
            "category": "DATABASE",
            "operation": "select_query",
            "parameters": {"table": "users"},
            "result": {"status": "SUCCESS"},
        },
        "performance": {
            "duration_ms": 123.45,
        },
        "error": {
            "occurred": False,
        },
    }


@pytest.fixture
def pii_test_data() -> Dict[str, Any]:
    """Create test data containing PII for sanitization testing.

    Returns:
        Dictionary with PII data
    """
    return {
        "password": "SecretPassword123!",
        "api_key": "xk_fake_abcdef1234567890abcdef1234567890",
        "credit_card": "4532-1234-5678-9010",
        "ssn": "123-45-6789",
        "email": "sensitive@example.com",
        "nested": {
            "pwd": "AnotherSecret",
            "user_email": "user@domain.com",
        },
        "list_data": [
            "public_data",
            "password=hidden123",
            {"secret": "token_xyz"},
        ],
    }


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset any singleton instances between tests.

    This prevents test pollution from singleton pattern usage.
    """
    # Reset any module-level singletons if they exist
    # This fixture runs automatically for all tests
    yield
    # Cleanup happens here if needed


@pytest.fixture
def mock_datetime(monkeypatch):
    """Mock datetime.utcnow for deterministic testing.

    Args:
        monkeypatch: Pytest monkeypatch fixture

    Returns:
        Function to set the mocked datetime
    """

    class MockDateTime:
        mock_now = datetime(2024, 1, 15, 10, 30, 0)

        @classmethod
        def utcnow(cls):
            return cls.mock_now

    def set_mock_datetime(dt: datetime):
        MockDateTime.mock_now = dt

    monkeypatch.setattr("vigil.core.event.datetime", MockDateTime)
    return set_mock_datetime

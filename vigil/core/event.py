"""Audit event data model."""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4


@dataclass
class SessionContext:
    """Session context information."""

    session_id: Optional[str] = None
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ActorContext:
    """Actor (user/system) context information."""

    type: str = "anonymous"  # user|system|service|anonymous
    id: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    roles: List[str] = field(default_factory=list)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ResourceInfo:
    """Resource information."""

    type: Optional[str] = None  # table|file|endpoint|function
    id: Optional[str] = None
    name: Optional[str] = None
    path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ActionResult:
    """Action result information."""

    status: str = "SUCCESS"  # SUCCESS|FAILURE|PARTIAL
    code: Optional[str] = None
    message: Optional[str] = None
    rows_affected: Optional[int] = None
    data_size_bytes: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ActionContext:
    """Action context information."""

    type: str = "EXECUTE"  # READ|WRITE|UPDATE|DELETE|EXECUTE|LOGIN|LOGOUT
    category: str = "SYSTEM"  # DATABASE|API|FILE|AUTH|SYSTEM
    operation: Optional[str] = None
    resource: ResourceInfo = field(default_factory=ResourceInfo)
    description: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: ActionResult = field(default_factory=ActionResult)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        data = asdict(self)
        # Convert nested dataclasses
        data["resource"] = self.resource.to_dict()
        data["result"] = self.result.to_dict()
        # Remove None values
        return {k: v for k, v in data.items() if v is not None}


@dataclass
class PerformanceMetrics:
    """Performance metrics."""

    duration_ms: Optional[float] = None
    cpu_time_ms: Optional[float] = None
    memory_mb: Optional[float] = None
    slow_query: bool = False
    threshold_exceeded: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ErrorInfo:
    """Error information."""

    occurred: bool = False
    type: Optional[str] = None
    message: Optional[str] = None
    stack_trace: Optional[str] = None
    handled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class AuditEvent:
    """Complete audit event structure."""

    # Core fields (always present)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = "1.0.0"

    # Context fields
    session: SessionContext = field(default_factory=SessionContext)
    actor: ActorContext = field(default_factory=ActorContext)
    action: ActionContext = field(default_factory=ActionContext)
    performance: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    error: ErrorInfo = field(default_factory=ErrorInfo)

    # Additional data
    system: Dict[str, Any] = field(default_factory=dict)
    custom: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
            "session": self.session.to_dict(),
            "actor": self.actor.to_dict(),
            "action": self.action.to_dict(),
            "performance": self.performance.to_dict(),
            "error": self.error.to_dict(),
            "system": self.system,
            "custom": self.custom,
            "metadata": self.metadata,
        }

    def to_json(self, indent: Optional[int] = None) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEvent":
        """Create event from dictionary.

        Args:
            data: Dictionary containing event data

        Returns:
            AuditEvent instance

        Raises:
            ValueError: If timestamp format is invalid or out of reasonable bounds
        """
        # Parse and validate timestamp
        if isinstance(data.get("timestamp"), str):
            try:
                data["timestamp"] = datetime.fromisoformat(data["timestamp"])
            except ValueError as e:
                raise ValueError(f"Invalid timestamp format: {e}")

        # Validate timestamp is reasonable (not too far in future or past)
        if isinstance(data.get("timestamp"), datetime):
            timestamp = data["timestamp"]
            now = datetime.now(timezone.utc)

            # Normalize both to aware or both to naive for comparison
            if timestamp.tzinfo is None:
                # Treat naive timestamps as UTC
                timestamp_cmp = timestamp.replace(tzinfo=timezone.utc)
            else:
                timestamp_cmp = timestamp

            # Allow some clock skew (1 hour in future)
            if timestamp_cmp > now + timedelta(hours=1):
                raise ValueError(
                    f"Timestamp is too far in the future: {timestamp.isoformat()}. "
                    f"Current time: {now.isoformat()}"
                )

            # Reject timestamps more than 100 years in the past
            if timestamp_cmp < now - timedelta(days=365 * 100):
                raise ValueError(f"Timestamp is too far in the past: {timestamp.isoformat()}")

        # Parse nested objects
        if "session" in data and isinstance(data["session"], dict):
            data["session"] = SessionContext(**data["session"])

        if "actor" in data and isinstance(data["actor"], dict):
            data["actor"] = ActorContext(**data["actor"])

        if "action" in data and isinstance(data["action"], dict):
            action_data = data["action"].copy()
            if "resource" in action_data and isinstance(action_data["resource"], dict):
                action_data["resource"] = ResourceInfo(**action_data["resource"])
            if "result" in action_data and isinstance(action_data["result"], dict):
                action_data["result"] = ActionResult(**action_data["result"])
            data["action"] = ActionContext(**action_data)

        if "performance" in data and isinstance(data["performance"], dict):
            data["performance"] = PerformanceMetrics(**data["performance"])

        if "error" in data and isinstance(data["error"], dict):
            data["error"] = ErrorInfo(**data["error"])

        # Filter out unknown fields to avoid TypeError on unexpected kwargs
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}

        return cls(**filtered)

    @classmethod
    def from_json(cls, json_str: str) -> "AuditEvent":
        """Create event from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

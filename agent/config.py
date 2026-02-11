"""Agent configuration."""

import logging
import os
import platform
from dataclasses import dataclass, fields

import yaml

logger = logging.getLogger(__name__)

_VALID_FIELD_NAMES = None  # lazily populated


@dataclass
class AgentConfig:
    """Configuration for the monitoring agent."""

    agent_id: str = os.environ.get("AGENT_ID", f"agent-{platform.node()}")
    collector_url: str = os.environ.get("COLLECTOR_URL", "http://localhost:8080")
    api_key: str = os.environ.get("AUDIT_API_KEY", "")
    interval_seconds: int = int(os.environ.get("INTERVAL_SECONDS", "30"))
    top_processes_count: int = int(os.environ.get("TOP_PROCESSES_COUNT", "5"))

    @classmethod
    def _field_names(cls) -> set:
        global _VALID_FIELD_NAMES
        if _VALID_FIELD_NAMES is None:
            _VALID_FIELD_NAMES = {f.name for f in fields(cls)}
        return _VALID_FIELD_NAMES

    @classmethod
    def from_yaml(cls, path: str) -> "AgentConfig":
        """Load configuration from a YAML file.

        Args:
            path: Path to YAML configuration file.

        Returns:
            Populated AgentConfig instance.

        Raises:
            FileNotFoundError: If the config file does not exist.
            ValueError: If the YAML is invalid or required sections/fields are missing.
        """
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path) as f:
            try:
                raw = yaml.safe_load(f)
            except yaml.YAMLError as exc:
                raise ValueError(f"Invalid YAML in config file {path}: {exc}") from exc

        if not isinstance(raw, dict) or "agent" not in raw:
            raise ValueError(f"Config file {path} is missing the required 'agent' section")

        agent_cfg = raw["agent"]
        if not isinstance(agent_cfg, dict):
            raise ValueError(
                f"The 'agent' section in {path} must be a mapping, got {type(agent_cfg).__name__}"
            )

        # Resolve environment variables in values
        resolved = {}
        valid = cls._field_names()
        for key, value in agent_cfg.items():
            if key not in valid:
                logger.debug("Ignoring unknown config key: %s", key)
                continue
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                resolved[key] = os.environ.get(env_var, "")
            else:
                resolved[key] = value

        # Validate numeric fields
        cls._validate_int_field(resolved, "interval_seconds", min_value=1)
        cls._validate_int_field(resolved, "top_processes_count", min_value=1)

        return cls(**resolved)

    @staticmethod
    def _validate_int_field(data: dict, name: str, min_value: int = 1) -> None:
        """Validate that a field, if present, is a positive integer.

        Raises:
            ValueError: If the value cannot be converted to int or is below min_value.
        """
        if name not in data:
            return

        value = data[name]
        try:
            int_val = int(value)
        except (TypeError, ValueError):
            raise ValueError(f"{name} must be an integer, got: {value!r}")

        if int_val < min_value:
            raise ValueError(f"{name} must be a positive integer (>= {min_value}), got: {int_val}")
        data[name] = int_val

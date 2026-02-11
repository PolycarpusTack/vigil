"""Configuration management for Vigil."""

import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from vigil.core.exceptions import ConfigurationError


class AuditConfig:
    """Vigil configuration manager."""

    # Default minimal configuration
    DEFAULT_CONFIG = {
        "vigil": {
            "core": {
                "enabled": True,
                "version": "1.0.0",
                "application_name": "app",
                "environment": "production",
            },
            "storage": {
                "backends": [
                    {
                        "type": "file",
                        "enabled": True,
                        "priority": 1,
                        "directory": "./logs/audit",
                        "format": "json",
                        "filename_pattern": "{app_name}_audit_{date}.log",
                        "rotation": {
                            "enabled": True,
                            "when": "midnight",
                            "backup_count": 30,
                            "compress": False,
                        },
                    }
                ]
            },
            "processing": {
                "sanitization": {"enabled": True},
                "filters": [],
            },
            "performance": {
                "async": {"enabled": False, "worker_threads": 2},
                "batching": {"enabled": False},
            },
        }
    }

    def __init__(self, config_file: Optional[str] = None, config_dict: Optional[Dict] = None):
        """
        Initialize configuration.

        Args:
            config_file: Path to YAML configuration file
            config_dict: Configuration dictionary (overrides file)
        """
        # Deep copy to avoid mutating shared defaults across instances
        self._config = deepcopy(self.DEFAULT_CONFIG)

        # Load from file if provided
        if config_file:
            self.load_from_file(config_file)

        # Override with dict if provided
        if config_dict:
            self.merge_config(config_dict)

        # Substitute environment variables
        self._substitute_env_vars()

    def load_from_file(self, config_file: str):
        """Load configuration from YAML file."""
        path = Path(config_file)
        if not path.exists():
            raise ConfigurationError(f"Configuration file not found: {config_file}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                file_config = yaml.safe_load(f)
                if file_config:
                    self.merge_config(file_config)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Failed to parse YAML configuration: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}")

    def merge_config(self, new_config: Dict[str, Any]):
        """Merge new configuration into existing config."""
        self._deep_merge(self._config, new_config)

    def _deep_merge(self, base: Dict, update: Dict):
        """Deep merge two dictionaries."""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def _substitute_env_vars(self):
        """Substitute environment variables in configuration values."""
        self._config = self._substitute_dict(self._config)

    def _substitute_dict(self, obj: Any) -> Any:
        """Recursively substitute environment variables in dict/list/str."""
        if isinstance(obj, dict):
            return {k: self._substitute_dict(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._substitute_dict(item) for item in obj]
        elif isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
            # Extract variable name: ${VAR_NAME} -> VAR_NAME
            var_name = obj[2:-1]
            value = os.environ.get(var_name)
            if value is None:
                raise ConfigurationError(
                    f"Environment variable '{var_name}' is not set but required in configuration"
                )
            return value
        return obj

    def get(self, path: str, default: Any = None) -> Any:
        """
        Get configuration value by path.

        Args:
            path: Dot-separated path (e.g., "vigil.core.enabled")
            default: Default value if path not found

        Returns:
            Configuration value or default
        """
        keys = path.split(".")
        value: Any = self._config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def set(self, path: str, value: Any):
        """
        Set configuration value by path.

        Args:
            path: Dot-separated path (e.g., "vigil.core.enabled")
            value: Value to set
        """
        keys = path.split(".")
        config: Any = self._config

        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        # Set the value
        config[keys[-1]] = value

    @property
    def enabled(self) -> bool:
        """Check if Vigil is enabled."""
        return self.get("vigil.core.enabled", True)

    @property
    def application_name(self) -> str:
        """Get application name."""
        return self.get("vigil.core.application_name", "app")

    @property
    def environment(self) -> str:
        """Get environment name."""
        return self.get("vigil.core.environment", "production")

    @property
    def storage_backends(self) -> list:
        """Get storage backend configurations."""
        return self.get("vigil.storage.backends", [])

    @property
    def async_enabled(self) -> bool:
        """Check if async processing is enabled."""
        return self.get("vigil.performance.async.enabled", False)

    @property
    def sanitization_enabled(self) -> bool:
        """Check if PII sanitization is enabled."""
        return self.get("vigil.processing.sanitization.enabled", True)

    def to_dict(self) -> Dict[str, Any]:
        """Return configuration as dictionary."""
        return self._config.copy()

    def __repr__(self) -> str:
        """String representation."""
        return f"AuditConfig(enabled={self.enabled}, app={self.application_name})"

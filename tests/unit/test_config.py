"""Unit tests for configuration handling.

Tests cover:
- Default configuration isolation
- YAML file loading
- Configuration merging
- Environment variable substitution
- Path-based get/set
- Property accessors
- Error handling
"""

import pytest
import yaml

from vigil.core.exceptions import ConfigurationError
from vigil.utils.config import AuditConfig


class TestDefaultConfig:
    """Tests for default configuration behavior."""

    def test_default_config_is_isolated_from_instance_mutations(self):
        """Ensure default config isn't mutated across instances."""
        custom_dir = "/tmp/custom_audit_logs"
        config1 = AuditConfig(
            config_dict={
                "vigil": {
                    "storage": {
                        "backends": [{"type": "file", "directory": custom_dir, "format": "json"}]
                    }
                }
            }
        )
        config2 = AuditConfig()
        assert config1.storage_backends[0]["directory"] == custom_dir
        assert config2.storage_backends[0]["directory"] == "./logs/audit"

    def test_default_enabled(self):
        """Default config has enabled=True."""
        config = AuditConfig()
        assert config.enabled is True

    def test_default_application_name(self):
        """Default application name is 'app'."""
        config = AuditConfig()
        assert config.application_name == "app"

    def test_default_environment(self):
        """Default environment is 'production'."""
        config = AuditConfig()
        assert config.environment == "production"

    def test_default_sanitization_enabled(self):
        """Sanitization is enabled by default."""
        config = AuditConfig()
        assert config.sanitization_enabled is True

    def test_default_async_disabled(self):
        """Async is disabled by default."""
        config = AuditConfig()
        assert config.async_enabled is False

    def test_default_storage_backends(self):
        """Default has one file storage backend."""
        config = AuditConfig()
        backends = config.storage_backends
        assert len(backends) == 1
        assert backends[0]["type"] == "file"


class TestConfigFromDict:
    """Tests for config_dict overrides."""

    def test_override_application_name(self):
        """Config dict overrides application name."""
        config = AuditConfig(
            config_dict={"vigil": {"core": {"application_name": "my-app"}}}
        )
        assert config.application_name == "my-app"

    def test_override_environment(self):
        """Config dict overrides environment."""
        config = AuditConfig(config_dict={"vigil": {"core": {"environment": "staging"}}})
        assert config.environment == "staging"

    def test_override_enabled(self):
        """Config dict can disable the framework."""
        config = AuditConfig(config_dict={"vigil": {"core": {"enabled": False}}})
        assert config.enabled is False

    def test_deep_merge_preserves_defaults(self):
        """Partial overrides preserve defaults for unset keys."""
        config = AuditConfig(
            config_dict={"vigil": {"core": {"application_name": "merged"}}}
        )
        # Should keep default environment
        assert config.environment == "production"
        # But override application name
        assert config.application_name == "merged"


class TestConfigFromFile:
    """Tests for YAML file loading."""

    def test_load_from_yaml_file(self, tmp_path):
        """Config loads values from YAML file."""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "vigil": {
                "core": {
                    "application_name": "yaml-app",
                    "environment": "test",
                },
            }
        }
        config_file.write_text(yaml.dump(config_data))

        config = AuditConfig(config_file=str(config_file))
        assert config.application_name == "yaml-app"
        assert config.environment == "test"

    def test_missing_file_raises_error(self):
        """ConfigurationError raised for missing config file."""
        with pytest.raises(ConfigurationError, match="not found"):
            AuditConfig(config_file="/nonexistent/config.yaml")

    def test_invalid_yaml_raises_error(self, tmp_path):
        """ConfigurationError raised for malformed YAML."""
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("key: [invalid\n  :")
        with pytest.raises(ConfigurationError, match="(?i)yaml"):
            AuditConfig(config_file=str(bad_file))

    def test_empty_yaml_file(self, tmp_path):
        """Empty YAML file does not crash (uses defaults)."""
        empty_file = tmp_path / "empty.yaml"
        empty_file.write_text("")
        config = AuditConfig(config_file=str(empty_file))
        # Should use defaults
        assert config.enabled is True


class TestEnvVarSubstitution:
    """Tests for ${ENV_VAR} substitution in config values."""

    def test_env_var_substituted(self, monkeypatch, tmp_path):
        """${VAR} syntax is resolved from environment."""
        monkeypatch.setenv("TEST_APP_NAME", "env-app")
        config_file = tmp_path / "env.yaml"
        config_data = {
            "vigil": {
                "core": {
                    "application_name": "${TEST_APP_NAME}",
                }
            }
        }
        config_file.write_text(yaml.dump(config_data))

        config = AuditConfig(config_file=str(config_file))
        assert config.application_name == "env-app"

    def test_missing_env_var_raises_error(self, monkeypatch, tmp_path):
        """Missing env var raises ConfigurationError."""
        monkeypatch.delenv("NONEXISTENT_CONFIG_VAR_XYZ", raising=False)
        config_file = tmp_path / "missing_env.yaml"
        config_data = {
            "vigil": {
                "core": {
                    "application_name": "${NONEXISTENT_CONFIG_VAR_XYZ}",
                }
            }
        }
        config_file.write_text(yaml.dump(config_data))

        with pytest.raises(ConfigurationError, match="NONEXISTENT_CONFIG_VAR_XYZ"):
            AuditConfig(config_file=str(config_file))


class TestPathBasedAccess:
    """Tests for get() and set() with dot-separated paths."""

    def test_get_existing_path(self):
        """Get returns value at a valid dot-path."""
        config = AuditConfig()
        assert config.get("vigil.core.enabled") is True

    def test_get_missing_path_returns_default(self):
        """Get returns default for non-existent path."""
        config = AuditConfig()
        assert config.get("vigil.nonexistent.key", "fallback") == "fallback"

    def test_get_missing_path_returns_none(self):
        """Get returns None when default not specified."""
        config = AuditConfig()
        assert config.get("vigil.nonexistent") is None

    def test_set_creates_path(self):
        """Set creates intermediate dicts and sets value."""
        config = AuditConfig()
        config.set("vigil.custom.new_key", "new_value")
        assert config.get("vigil.custom.new_key") == "new_value"

    def test_set_overwrites_existing(self):
        """Set overwrites an existing value."""
        config = AuditConfig()
        config.set("vigil.core.enabled", False)
        assert config.get("vigil.core.enabled") is False


class TestMergeConfig:
    """Tests for deep merge behavior."""

    def test_merge_adds_new_keys(self):
        """Merge adds keys that don't exist in base."""
        config = AuditConfig()
        config.merge_config({"vigil": {"custom_section": {"key": "value"}}})
        assert config.get("vigil.custom_section.key") == "value"

    def test_merge_overwrites_leaf_values(self):
        """Merge overwrites leaf values."""
        config = AuditConfig()
        config.merge_config({"vigil": {"core": {"application_name": "merged"}}})
        assert config.application_name == "merged"

    def test_merge_preserves_sibling_keys(self):
        """Merge preserves sibling keys not in the update."""
        config = AuditConfig()
        config.merge_config({"vigil": {"core": {"application_name": "merged"}}})
        # enabled should still be True (not overwritten)
        assert config.enabled is True


class TestToDict:
    """Tests for serialization."""

    def test_to_dict_returns_dict(self):
        """to_dict returns a dictionary."""
        config = AuditConfig()
        d = config.to_dict()
        assert isinstance(d, dict)
        assert "vigil" in d

    def test_repr(self):
        """repr includes key info."""
        config = AuditConfig()
        r = repr(config)
        assert "AuditConfig" in r
        assert "enabled=" in r

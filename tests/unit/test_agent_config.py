"""Unit tests for agent configuration loading and validation.

Tests cover:
- Missing config file
- Invalid YAML syntax
- Missing agent section
- Unknown keys handling
- Environment variable substitution
- Numeric field validation
- Valid minimal and full configs
"""

import pytest
import yaml

from agent.config import AgentConfig


@pytest.fixture
def write_yaml(tmp_path):
    """Helper fixture that writes a YAML file and returns the path."""

    def _write(data: dict, filename: str = "agent.yaml") -> str:
        path = tmp_path / filename
        path.write_text(yaml.dump(data))
        return str(path)

    return _write


class TestFromYamlFileErrors:
    """Tests for file-level errors in from_yaml."""

    def test_from_yaml_missing_file(self, tmp_path):
        """FileNotFoundError raised with clear message when file does not exist."""
        missing = str(tmp_path / "nonexistent.yaml")
        with pytest.raises(FileNotFoundError, match="nonexistent.yaml"):
            AgentConfig.from_yaml(missing)

    def test_from_yaml_invalid_yaml(self, tmp_path):
        """ValueError raised when file contains invalid YAML."""
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("agent:\n  interval_seconds: [invalid\n  :")
        with pytest.raises(ValueError, match="(?i)invalid.*yaml"):
            AgentConfig.from_yaml(str(bad_file))


class TestFromYamlStructureValidation:
    """Tests for YAML structure validation."""

    def test_from_yaml_missing_agent_section(self, write_yaml):
        """ValueError raised when YAML has no 'agent' section."""
        path = write_yaml({"logging": {"level": "INFO"}})
        with pytest.raises(ValueError, match="(?i)agent.*section"):
            AgentConfig.from_yaml(path)

    def test_from_yaml_ignores_unknown_keys(self, write_yaml):
        """Unknown keys under agent section are silently ignored."""
        path = write_yaml(
            {
                "agent": {
                    "collector_url": "http://example.com",
                    "unknown_key": "should_be_ignored",
                    "another_unknown": 42,
                }
            }
        )
        config = AgentConfig.from_yaml(path)
        assert config.collector_url == "http://example.com"
        assert not hasattr(config, "unknown_key")


class TestFromYamlEnvVarSubstitution:
    """Tests for ${ENV_VAR} substitution in YAML values."""

    def test_from_yaml_env_var_substitution(self, write_yaml, monkeypatch):
        """Environment variable references are resolved."""
        monkeypatch.setenv("TEST_COLLECTOR_URL", "http://from-env:9090")
        path = write_yaml(
            {
                "agent": {
                    "collector_url": "${TEST_COLLECTOR_URL}",
                }
            }
        )
        config = AgentConfig.from_yaml(path)
        assert config.collector_url == "http://from-env:9090"

    def test_from_yaml_env_var_missing_uses_default(self, write_yaml, monkeypatch):
        """Unset env var falls back to empty string."""
        monkeypatch.delenv("NONEXISTENT_VAR_12345", raising=False)
        path = write_yaml(
            {
                "agent": {
                    "api_key": "${NONEXISTENT_VAR_12345}",
                }
            }
        )
        config = AgentConfig.from_yaml(path)
        assert config.api_key == ""


class TestFromYamlFieldValidation:
    """Tests for individual field validation."""

    def test_from_yaml_invalid_interval(self, write_yaml):
        """ValueError raised when interval_seconds is zero or negative."""
        path = write_yaml({"agent": {"interval_seconds": 0}})
        with pytest.raises(ValueError, match="(?i)interval_seconds.*positive"):
            AgentConfig.from_yaml(path)

        path2 = write_yaml({"agent": {"interval_seconds": -5}}, filename="neg.yaml")
        with pytest.raises(ValueError, match="(?i)interval_seconds.*positive"):
            AgentConfig.from_yaml(path2)

    def test_from_yaml_non_numeric_interval(self, write_yaml):
        """ValueError raised when interval_seconds is not a number."""
        path = write_yaml({"agent": {"interval_seconds": "fast"}})
        with pytest.raises(ValueError, match="(?i)interval_seconds.*integer"):
            AgentConfig.from_yaml(path)


class TestFromYamlValidConfigs:
    """Tests for valid configuration loading."""

    def test_from_yaml_minimal_valid(self, write_yaml):
        """Minimal config (just agent section) uses defaults for missing fields."""
        path = write_yaml({"agent": {}})
        config = AgentConfig.from_yaml(path)
        assert isinstance(config, AgentConfig)
        assert config.interval_seconds == 30  # default
        assert config.top_processes_count == 5  # default

    def test_from_yaml_full_valid(self, write_yaml):
        """All fields are correctly populated from YAML."""
        path = write_yaml(
            {
                "agent": {
                    "agent_id": "server-01",
                    "collector_url": "http://collector:8080",
                    "api_key": "secret-key-123",
                    "interval_seconds": 60,
                    "top_processes_count": 10,
                }
            }
        )
        config = AgentConfig.from_yaml(path)
        assert config.agent_id == "server-01"
        assert config.collector_url == "http://collector:8080"
        assert config.api_key == "secret-key-123"
        assert config.interval_seconds == 60
        assert config.top_processes_count == 10

# Spec: Add Config Validation to AgentConfig
- component: agent
- status: done
- priority: P2-medium
- depends-on: []
- debt-tag: DEBT:TD-06 No config validation in AgentConfig.from_yaml()

## Problem
`AgentConfig.from_yaml()` does not validate the loaded YAML. If the file is missing, contains invalid YAML, or lacks required fields, the error messages are unhelpful (bare `FileNotFoundError`, `yaml.YAMLError`, or `TypeError` from dataclass `__init__`). The method should provide clear, actionable error messages.

## Acceptance Criteria

| # | Given | When | Then | Test Name |
|---|-------|------|------|-----------|
| AC1 | The YAML file does not exist | `from_yaml()` is called | A `FileNotFoundError` with a clear message is raised | `test_from_yaml_missing_file` |
| AC2 | The YAML file contains invalid YAML | `from_yaml()` is called | A `ValueError` with a clear message is raised | `test_from_yaml_invalid_yaml` |
| AC3 | The YAML file is valid but has no `agent` section | `from_yaml()` is called | A `ValueError` is raised indicating the missing section | `test_from_yaml_missing_agent_section` |
| AC4 | The YAML file has unknown keys under `agent` | `from_yaml()` is called | Unknown keys are ignored without error | `test_from_yaml_ignores_unknown_keys` |
| AC5 | A YAML value uses `${ENV_VAR}` syntax | `from_yaml()` is called with env var set | The value is resolved from the environment | `test_from_yaml_env_var_substitution` |
| AC6 | A YAML value uses `${ENV_VAR}` but the var is not set | `from_yaml()` is called | The value falls back to field default or empty string | `test_from_yaml_env_var_missing_uses_default` |
| AC7 | `interval_seconds` is negative or zero | `from_yaml()` is called | A `ValueError` is raised | `test_from_yaml_invalid_interval` |
| AC8 | `interval_seconds` is a non-numeric string | `from_yaml()` is called | A `ValueError` is raised | `test_from_yaml_non_numeric_interval` |
| AC9 | A valid minimal YAML is provided | `from_yaml()` is called | Config loads with defaults for unspecified fields | `test_from_yaml_minimal_valid` |
| AC10 | A fully specified YAML is provided | `from_yaml()` is called | All fields are correctly populated | `test_from_yaml_full_valid` |

## Files Affected
- MODIFY: `agent/config.py` (add validation logic)
- CREATE: `tests/unit/test_agent_config.py` (new test file)

## Security Checklist
- [x] S1 Input validation
- [x] S5 Error messages safe

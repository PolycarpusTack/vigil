# Spec: Expand Config Tests
- component: core
- status: done
- priority: P2-medium
- depends-on: []
- debt-tag: none

## Problem
`tests/unit/test_config.py` has only 1 test for `AuditConfig`. The config module handles YAML loading, env var substitution, deep merging, and path-based get/set — all untested.

## Files Affected
- MODIFY: `tests/unit/test_config.py`

# Spec: Configurable Disk Path
- component: agent
- status: done
- priority: P2-medium
- depends-on: []
- debt-tag: DEBT:TD-05 collect_disk() hardcodes / path

## Problem
`collect_disk()` defaults to `/` which fails on Windows. The path should be configurable and auto-detect the platform default.

## Acceptance Criteria

| # | Given | When | Then | Test Name |
|---|-------|------|------|-----------|
| AC1 | A custom disk path is provided | collect_disk(path) is called | Metrics for that path are returned | `test_disk_custom_path` |
| AC2 | An invalid disk path is provided | collect_disk(path) is called | A meaningful error is raised | `test_disk_invalid_path` |
| AC3 | No path is provided | collect_disk() is called | The platform default root is used | `test_disk_default_path_cross_platform` |

## Files Affected
- MODIFY: `agent/collectors/disk.py`
- MODIFY: `tests/unit/test_agent_collectors.py`

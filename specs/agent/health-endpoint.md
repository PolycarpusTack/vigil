# Spec: Agent Health Endpoint
- component: agent
- status: done
- priority: P2-medium
- depends-on: []
- debt-tag: none

## Problem
The monitoring agent runs as a background daemon but has no way to expose its current health status. Operators cannot tell if the agent is running, collecting successfully, or failing to reach the collector without reading logs.

## Acceptance Criteria

| # | Given | When | Then | Test Name |
|---|-------|------|------|-----------|
| AC1 | Agent health tracker is created | Status is queried | Returns a health dict with agent_id, status, uptime_seconds, last_collection_time, last_send_success, and consecutive_failures | `test_health_status_initial` |
| AC2 | Agent has collected metrics successfully | Status is queried | last_collection_time is set and last_send_success is True | `test_health_status_after_successful_send` |
| AC3 | Agent send has failed | Status is queried | last_send_success is False and consecutive_failures increments | `test_health_status_after_failed_send` |
| AC4 | Agent send fails then succeeds | Status is queried | consecutive_failures resets to 0 | `test_consecutive_failures_reset_on_success` |
| AC5 | Agent has been running for some time | Uptime is queried | uptime_seconds reflects elapsed time | `test_uptime_increases` |
| AC6 | Health status is degraded (>3 failures) | Status field is checked | status is "degraded" | `test_status_degraded_after_threshold` |
| AC7 | Health status is healthy (0 failures) | Status field is checked | status is "healthy" | `test_status_healthy` |

## Files Affected
- CREATE: `agent/health.py`
- CREATE: `tests/unit/test_agent_health.py`
- MODIFY: `agent/main.py` (integrate health tracker into collection loop)

# Spec: Agent Integration Test with Mocked Collector
- component: agent
- status: done
- priority: P2-medium
- depends-on: [specs/agent/debt-td-04-retry-backoff.md, specs/agent/health-endpoint.md]
- debt-tag: none

## Problem
The existing agent-to-collector integration test only covers the happy path (collect real metrics → POST → GET). It doesn't test how the agent's HTTPSender and HealthTracker behave when the collector returns errors, times out, or is unavailable. These scenarios are critical for production reliability.

## Acceptance Criteria

| # | Given | When | Then | Test Name |
|---|-------|------|------|-----------|
| AC1 | Collector returns 201 | HTTPSender.send_metrics() called | returns True | `test_sender_succeeds_on_201` |
| AC2 | Collector returns 500 then 201 | HTTPSender.send_metrics() called | retries and returns True | `test_sender_retries_on_500_then_succeeds` |
| AC3 | Collector returns 500 on all attempts | HTTPSender.send_metrics() called 3 times | returns False | `test_sender_fails_after_max_retries` |
| AC4 | Collector returns 401 | HTTPSender.send_metrics() called | returns False immediately (no retry) | `test_sender_no_retry_on_401` |
| AC5 | Collector returns 429 then 201 | HTTPSender.send_metrics() called | retries and returns True | `test_sender_retries_on_429` |
| AC6 | Collector unreachable | HTTPSender.send_metrics() called | retries then returns False | `test_sender_retries_on_connection_error` |
| AC7 | collect_all_metrics called | returns payload dict | has all expected keys (agent_id, hostname, timestamp, metrics) | `test_collect_all_metrics_has_required_keys` |
| AC8 | Agent run loop with collector returning 201 | one collection cycle | health status is healthy | `test_run_loop_healthy_on_success` |
| AC9 | Agent run loop with collector failing | consecutive failures | health status is degraded | `test_run_loop_degraded_on_failures` |

## Files Affected
- MODIFY: `tests/integration/test_agent_to_collector.py` (add new test classes)

## Schema Impact
- [x] No schema changes

## Security Checklist (S5)
- [x] S1-S5 all N/A for tests

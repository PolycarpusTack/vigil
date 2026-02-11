# Spec: Collector Internal Metrics Endpoint
- component: collector
- status: done
- priority: P2-medium
- depends-on: []
- debt-tag: none

## Problem
The collector service has no observability into its own operational health. There is no endpoint to query request counts, error counts, or latency percentiles for the service itself. Operators cannot distinguish between "no events arriving" and "collector is down".

## Acceptance Criteria

| # | Given | When | Then | Test Name |
|---|-------|------|------|-----------|
| AC1 | Collector is running | GET /api/v1/internal/metrics is called | Returns request_count, error_count, uptime_seconds | `test_internal_metrics_returns_counters` |
| AC2 | Events have been ingested | GET /api/v1/internal/metrics is called | request_count reflects the number of requests | `test_internal_metrics_request_count_increments` |
| AC3 | A request has failed | GET /api/v1/internal/metrics is called | error_count reflects failures | `test_internal_metrics_error_count` |
| AC4 | Collector just started | GET /api/v1/internal/metrics is called | uptime_seconds >= 0 | `test_internal_metrics_uptime` |
| AC5 | Internal metrics endpoint is called | No auth header | Still returns metrics (monitoring endpoint, no auth needed) | `test_internal_metrics_no_auth_required` |

## Files Affected
- CREATE: `collector/api/internal_metrics.py`
- CREATE: `collector/middleware/metrics_tracker.py`
- MODIFY: `collector/main.py` (register router + middleware)
- MODIFY: `tests/integration/test_collector_api.py` (add internal metrics tests)

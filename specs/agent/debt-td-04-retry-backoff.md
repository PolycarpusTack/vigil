# Spec: Add Retry with Exponential Backoff to HTTPSender
- component: agent
- status: done
- priority: P2-medium
- depends-on: []
- debt-tag: DEBT:TD-04 No retry/backoff in http_sender.py

## Problem
`HTTPSender.send_metrics()` makes a single attempt. If the collector returns a transient error (500, timeout, connection error), the metric is lost.

## Acceptance Criteria

| # | Given | When | Then | Test Name |
|---|-------|------|------|-----------|
| AC1 | Collector returns 500 twice then 201 | send_metrics is called | It retries and ultimately succeeds | `test_send_metrics_retries_on_server_error` |
| AC2 | Collector returns 500 three times | send_metrics is called | It returns False after max retries | `test_send_metrics_gives_up_after_max_retries` |
| AC3 | Collector times out once then succeeds | send_metrics is called | It retries and succeeds | `test_send_metrics_retries_on_timeout` |
| AC4 | Collector returns 201 on first attempt | send_metrics is called | No retry, returns True | `test_send_metrics_no_retry_on_success` |

## Files Affected
- MODIFY: `agent/transport/http_sender.py` (add retry logic)
- CREATE: `tests/unit/test_http_sender.py` (new test file)

## Security Checklist
- [x] S1 Input validation

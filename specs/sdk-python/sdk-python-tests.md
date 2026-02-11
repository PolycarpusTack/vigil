# Spec: Python SDK Test Suite
- component: sdk-python
- status: done
- priority: P1-high
- depends-on: []
- debt-tag: DEBT:TD-11 Zero test coverage for Python SDK

## Problem
The Python SDK (`sdks/python/audit_sdk/client.py`) has 0% test coverage. Cannot verify correctness of log, log_batch, log_audit_event, auth header, or error handling.

## Acceptance Criteria

| # | Given | When | Then | Test Name |
|---|-------|------|------|-----------|
| AC1 | A valid AuditClient | log() is called | A POST request is made to /api/v1/events with correct payload | `test_log_sends_event` |
| AC2 | A valid AuditClient | log_batch() is called with events | POST to /api/v1/events/batch with correct payload | `test_log_batch_sends_events` |
| AC3 | A valid AuditClient | log_audit_event() is called with AuditEvent | POST with event.to_dict() payload | `test_log_audit_event_sends_event_dict` |
| AC4 | AuditClient with api_key | Any request is made | Authorization: Bearer header is present | `test_auth_header_is_set` |
| AC5 | Server returns 401 | log() is called | HTTPError is raised | `test_log_raises_on_auth_error` |
| AC6 | Server returns 500 | log() is called | HTTPError is raised | `test_log_raises_on_server_error` |
| AC7 | AuditClient used as context manager | Exiting the context | Session is closed | `test_context_manager_closes_session` |
| AC8 | AuditClient.log() | No timestamp provided | Timestamp is auto-generated in UTC | `test_log_auto_generates_timestamp` |

## Files Affected
- CREATE: `tests/unit/test_python_sdk.py`

## Schema Impact
- [x] No schema changes

## Security Checklist
- [x] S1 Input validation
- [x] S3 No secrets in code (tests use mock)

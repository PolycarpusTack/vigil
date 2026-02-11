# Spec: Python SDK Edge Case Tests
- component: sdk-python
- status: done
- priority: P2-medium
- depends-on: [specs/sdk-python/sdk-python-tests.md]
- debt-tag: none

## Problem
The Python SDK has basic test coverage for happy path and simple error scenarios (401/500), but lacks edge case tests for network failures, timeouts, invalid responses, boundary inputs, and session lifecycle issues. These are critical for SDK reliability in production.

## Acceptance Criteria

| # | Given | When | Then | Test Name |
|---|-------|------|------|-----------|
| AC1 | SDK client configured with 5s timeout | connection hangs beyond timeout | ConnectTimeout is raised | `test_log_raises_on_connect_timeout` |
| AC2 | SDK client configured with 5s timeout | server takes too long to respond | ReadTimeout is raised | `test_log_raises_on_read_timeout` |
| AC3 | Collector is unreachable | log() is called | ConnectionError is raised | `test_log_raises_on_connection_refused` |
| AC4 | Server returns invalid JSON | log() is called | ValueError/JSONDecodeError raised | `test_log_handles_invalid_json_response` |
| AC5 | log_batch called with empty list | batch is sent | POST is still made with empty events list | `test_log_batch_empty_list` |
| AC6 | log_batch called with 100 events | batch is sent | all 100 events included in payload | `test_log_batch_max_size` |
| AC7 | Unicode characters in event fields | log() is called | unicode preserved in payload | `test_log_preserves_unicode` |
| AC8 | Custom event_id and timestamp provided | log() is called | custom values are used, not auto-generated | `test_log_uses_custom_event_id_and_timestamp` |
| AC9 | Client used for multiple sequential calls | log() called twice | same session reused for both requests | `test_session_reused_across_calls` |
| AC10 | Collector URL has multiple trailing slashes | client initialized | base_url has no trailing slashes | `test_base_url_strips_multiple_trailing_slashes` |
| AC11 | User metadata key conflicts with app/env | log() called with metadata containing "application" | user value takes precedence (setdefault) | `test_user_metadata_takes_precedence` |
| AC12 | log_audit_event with object missing to_dict | called | AttributeError raised | `test_log_audit_event_invalid_object` |
| AC13 | log_batch connection error | batch send fails | ConnectionError raised | `test_log_batch_raises_on_connection_error` |
| AC14 | Timeout passed to session.post | log() called | timeout value forwarded to post() | `test_timeout_passed_to_requests` |
| AC15 | Context manager with exception | exception inside with block | session still closed | `test_context_manager_closes_on_exception` |

## Files Affected
- MODIFY: `tests/unit/test_python_sdk.py` (add new test class)

## Schema Impact
- [x] No schema changes

## Security Checklist (S5)
- [x] S1 Input validation (SDK validates nothing - passthrough to collector)
- [x] S2 Auth/authz (tested in existing tests)
- [x] S3 No secrets in code
- [x] S4 SQL parameterized (N/A - SDK has no SQL)
- [x] S5 Error messages safe

# Spec: Integrate AuditEngine in Collector Event Ingest
- component: collector
- status: done
- priority: P1-high
- depends-on: [specs/core/debt-td-15-api-key-regex.md]
- debt-tag: DEBT:TD-01 Collector bypasses core AuditEngine

## Problem
The collector's event ingest endpoint stores events directly to the database without running them through the core `AuditEngine` processing pipeline. This means PII sanitization is bypassed for events ingested via the API.

## Acceptance Criteria

| # | Given | When | Then | Test Name |
|---|-------|------|------|-----------|
| AC1 | An event containing PII (email in metadata) | It is ingested via POST /api/v1/events | The stored event has the email redacted | `test_ingested_event_has_pii_sanitized` |
| AC2 | An event containing an API key in parameters | It is ingested via POST /api/v1/events | The stored event has the key redacted | `test_ingested_event_api_key_sanitized` |

## Files Affected
- MODIFY: `collector/api/events.py` (add AuditEngine processing in _store_event)
- MODIFY: `collector/main.py` (initialize AuditEngine on startup)
- MODIFY: `tests/integration/test_collector_api.py` (add PII sanitization tests)

## Schema Impact
- [x] No schema changes

## Security Checklist
- [x] S1 Input validation
- [x] S6 PII sanitisation - this is the fix

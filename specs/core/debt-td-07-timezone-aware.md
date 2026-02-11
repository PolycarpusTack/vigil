# Spec: Standardize on Timezone-Aware UTC Timestamps
- component: core
- status: done
- priority: P2-medium
- depends-on: []
- debt-tag: DEBT:TD-07 Mixed naive/aware datetime usage

## Problem
The codebase mixes `datetime.utcnow()` (naive) and `datetime.now(timezone.utc)` (aware). This causes `TypeError` when comparing naive and aware datetimes (e.g. in `AuditEvent.from_dict` timestamp validation).

## Acceptance Criteria

| # | Given | When | Then | Test Name |
|---|-------|------|------|-----------|
| AC1 | An AuditEvent is created with defaults | The timestamp field is inspected | It is timezone-aware (has tzinfo) | `test_event_default_timestamp_is_timezone_aware` |
| AC2 | A timezone-aware ISO timestamp string is parsed | AuditEvent.from_dict processes it | No TypeError on comparison | `test_from_dict_timezone_aware_timestamp_accepted` |
| AC3 | A naive ISO timestamp string is parsed | AuditEvent.from_dict processes it | Comparison works (naive assumed UTC) | `test_from_dict_naive_timestamp_accepted` |

## Files Affected
- MODIFY: `vigil/core/event.py` (datetime.utcnow -> datetime.now(timezone.utc))
- MODIFY: `collector/api/events.py` (datetime.utcnow -> datetime.now(timezone.utc))
- MODIFY: `tests/conftest.py` (mock_datetime fixture)
- MODIFY: `tests/unit/test_event.py` (update tests)

## Schema Impact
- [x] No schema changes

## Security Checklist
- [x] S1 Input validation
- [x] S5 Error messages safe

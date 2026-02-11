# Spec: Collector Code Cleanup (TD-08, TD-09)
- component: collector
- status: done
- priority: P3-low
- depends-on: []
- debt-tag: DEBT:TD-08 health.py import at bottom; DEBT:TD-09 unused _event_to_response helper

## Problem
- `health.py` has `from sqlalchemy import text as sa_text` at the bottom of the file (line 28) — PEP 8 violation
- `events.py` has `_event_to_response()` helper that is defined but never called — dead code

## Acceptance Criteria

| # | Given | When | Then | Test Name |
|---|-------|------|------|-----------|
| AC1 | health.py import moved to top | Readiness check is called | It still works correctly | existing integration tests |
| AC2 | _event_to_response removed | All event endpoints called | They still work correctly | existing integration tests |

## Files Affected
- MODIFY: `collector/api/health.py` (move import to top)
- MODIFY: `collector/api/events.py` (remove unused helper)

## Security Checklist
- [x] S1 Input validation

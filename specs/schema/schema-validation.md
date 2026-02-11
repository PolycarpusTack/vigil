# Spec: JSON Schema Contract Validation
- component: schema
- status: done
- priority: P2-medium
- depends-on: []
- debt-tag: none

## Problem
No tests validate that Python `AuditEvent.to_dict()` output conforms to `schema/audit_event.schema.json`. Schema drift between code and schema is undetected.

## Acceptance Criteria

| # | Given | When | Then | Test Name |
|---|-------|------|------|-----------|
| AC1 | A default AuditEvent | to_dict() is validated against schema | No validation error | `test_default_event_conforms_to_schema` |
| AC2 | A fully populated AuditEvent | to_dict() is validated against schema | No validation error | `test_full_event_conforms_to_schema` |
| AC3 | An event with invalid action type | Validated against schema | Validation error raised | `test_invalid_action_type_rejected` |
| AC4 | Schema enums | Compared to Python enums | They match exactly | `test_schema_action_types_match_python_enums` |
| AC5 | Schema enums | Compared to Python enums | They match exactly | `test_schema_categories_match_python_enums` |

## Files Affected
- CREATE: `tests/contract/test_schema_validation.py`
- MODIFY: `schema/audit_event.schema.json` (update enums to match Python)

## Security Checklist
- [x] S1 Input validation

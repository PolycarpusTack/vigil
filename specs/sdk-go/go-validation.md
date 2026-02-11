# Spec: Go SDK Enum Validation
- component: sdk-go
- status: done
- priority: P2-medium
- depends-on: []
- debt-tag: DEBT:TD-12 No enum validation — accepts invalid action types

## Problem
The Go SDK accepts any string for `Action.Type` and `Action.Category`. Invalid values are silently sent to the collector, which may reject or misclassify them.

## Acceptance Criteria

| # | Given | When | Then | Test Name |
|---|-------|------|------|-----------|
| AC1 | An event with invalid action type | Validate() is called | An error is returned listing invalid type | `TestValidateEvent_InvalidActionType` |
| AC2 | An event with invalid category | Validate() is called | An error is returned listing invalid category | `TestValidateEvent_InvalidCategory` |
| AC3 | An event with valid type and category | Validate() is called | No error | `TestValidateEvent_Valid` |
| AC4 | An event with empty operation | Validate() is called | An error is returned | `TestValidateEvent_EmptyOperation` |
| AC5 | Client.Log validates before sending | Log() is called with invalid event | An error is returned without HTTP call | `TestLog_ValidationError` |

## Files Affected
- CREATE: `sdks/go/audit/validate.go`
- MODIFY: `sdks/go/audit/client.go` (add validation call)
- CREATE: `sdks/go/audit/validate_test.go`

## Security Checklist
- [x] S1 Input validation

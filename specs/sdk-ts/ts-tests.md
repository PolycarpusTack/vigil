# Spec: TypeScript SDK Tests
- component: sdk-ts
- status: done
- priority: P2-medium
- depends-on: []
- debt-tag: DEBT:TD-13 No tests for TypeScript SDK

## Problem
The TypeScript SDK has zero test coverage. Additionally, the ActionContext type unions are incomplete compared to the Python enums — missing several valid action types and categories.

## Acceptance Criteria

| # | Given | When | Then | Test Name |
|---|-------|------|------|-----------|
| AC1 | Valid options | AuditClient is constructed | Properties are set correctly | `constructor sets properties` |
| AC2 | AuditClient.log() is called | fetch succeeds | The correct endpoint is called with event payload | `log sends event to collector` |
| AC3 | AuditClient.logBatch() is called | fetch succeeds | The batch endpoint is called | `logBatch sends batch to collector` |
| AC4 | Collector returns 500 | log() is called | An error is thrown | `log throws on server error` |
| AC5 | Timeout fires | log() is called | An error is thrown | `log throws on timeout` |
| AC6 | API key is set | log() is called | Authorization header is included | `log sends auth header` |
| AC7 | Types are complete | ActionContext.type union | All 14 Python action types are valid | type alignment verified |

## Files Affected
- MODIFY: `sdks/typescript/src/types.ts` (complete the ActionContext unions)
- CREATE: `sdks/typescript/src/__tests__/client.test.ts`
- MODIFY: `sdks/typescript/package.json` (add test script and vitest)

## Security Checklist
- [x] S1 Input validation

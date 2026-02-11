# Spec: E2E Docker Compose Test
- component: infra
- status: done
- priority: P2-medium
- depends-on: []
- debt-tag: none

## Problem
There is no automated end-to-end test that boots the full stack and verifies that events flow from client to database. Failures in integration between collector, database, and authentication are only caught manually.

## Acceptance Criteria

| # | Given | When | Then | Test Name |
|---|-------|------|------|-----------|
| AC1 | Docker compose stack is up | Health endpoint is called | Returns 200 status ok | E2E: health check |
| AC2 | Stack is up and authenticated | An event is POSTed | Returns 201 accepted | E2E: event ingest |
| AC3 | An event was ingested | Event is queried by ID | Returns the event | E2E: event retrieval |
| AC4 | Stack is up | Internal metrics is called | Returns request_count and uptime | E2E: internal metrics |
| AC5 | Stack is up | Batch events are POSTed | Returns 201 with correct accepted count | E2E: batch ingest |

## Files Affected
- CREATE: `tests/e2e/test_full_stack.sh`
- MODIFY: `docker-compose.yml` (no changes needed — already has collector + db + agent)

## Notes
- Script uses `curl` and `jq` for assertions
- Script manages docker-compose lifecycle (up → test → down)
- Exit code 0 = all pass, 1 = any failure

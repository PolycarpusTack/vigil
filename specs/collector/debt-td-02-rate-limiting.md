# Spec: Add Rate Limiting to Collector
- component: collector
- status: done
- priority: P1-high
- depends-on: []
- debt-tag: DEBT:TD-02 No rate limiting on any endpoint

## Problem
The collector has no rate limiting, making it vulnerable to DoS attacks. Auth failures and ingest endpoints should be rate-limited.

## Acceptance Criteria

| # | Given | When | Then | Test Name |
|---|-------|------|------|-----------|
| AC1 | Rate limit is configured | A client exceeds the rate limit | 429 Too Many Requests is returned | `test_rate_limit_exceeded_returns_429` |
| AC2 | Rate limit is configured | Requests are within the limit | Requests succeed normally | (existing tests) |

## Files Affected
- CREATE: `collector/middleware/rate_limit.py`
- MODIFY: `collector/main.py` (add middleware)
- MODIFY: `tests/integration/test_collector_api.py` (add rate limit test)

## Security Checklist
- [x] S7 Rate limiting - this is the fix

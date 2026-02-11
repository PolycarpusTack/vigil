# Spec: CORS Configuration
- component: collector
- status: done
- priority: P2-medium
- depends-on: []
- debt-tag: none

## Problem
The collector has no CORS middleware. When exposed beyond localhost, browser-based SDKs or dashboards cannot access the API due to missing CORS headers.

## Acceptance Criteria

| # | Given | When | Then | Test Name |
|---|-------|------|------|-----------|
| AC1 | CORS is configured via env var | An OPTIONS preflight request is sent | CORS headers are returned | `test_cors_preflight_returns_headers` |
| AC2 | CORS_ORIGINS is not set | A request is made | Default restrictive origins used (localhost only) | `test_cors_default_localhost_only` |
| AC3 | CORS_ORIGINS is set | A request from allowed origin | Access-Control-Allow-Origin header present | `test_cors_allowed_origin` |

## Files Affected
- MODIFY: `collector/main.py` (add CORSMiddleware)
- MODIFY: `collector/config.py` (add cors_origins field)
- MODIFY: `tests/integration/test_collector_api.py` (add CORS tests)

## Security Checklist
- [x] S8 CORS: explicit origin allowlist

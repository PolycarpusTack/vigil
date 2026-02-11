# Spec: Remove Dev-Mode Auth Bypass
- component: collector
- status: done
- priority: P1-high
- depends-on: []
- debt-tag: DEBT:TD-03 Dev-mode auth bypass when no API keys configured

## Problem
When no API keys are configured, `verify_api_key()` returns `"no-auth"` allowing all requests. In a misconfigured deployment, this means unauthenticated access. The bypass should require explicit `AUTH_DISABLED=true` env var.

## Acceptance Criteria

| # | Given | When | Then | Test Name |
|---|-------|------|------|-----------|
| AC1 | No API keys configured and AUTH_DISABLED not set | A request is made with a Bearer token | The request is rejected with 401 | `test_no_keys_configured_rejects_requests` |
| AC2 | AUTH_DISABLED=true is set | A request is made with any Bearer token | The request is allowed | `test_auth_disabled_allows_requests` |
| AC3 | API keys configured | A valid Bearer token is sent | The request is allowed | (existing test) |

## Files Affected
- MODIFY: `collector/auth/api_keys.py` (remove bypass, add AUTH_DISABLED check)
- MODIFY: `tests/integration/test_collector_api.py` (add test)

## Security Checklist
- [x] S2 Auth/authz - this is the fix
- [x] S3 No secrets in code

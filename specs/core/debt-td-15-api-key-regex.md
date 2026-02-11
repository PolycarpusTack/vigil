# Spec: Fix API Key Regex to Match Keys with Underscores and Dashes
- component: core
- status: done
- priority: P1-high
- depends-on: []
- debt-tag: DEBT:TD-15 API key regex doesn't match keys with _ or -

## Problem
The API key regex in PIISanitizer uses `[a-zA-Z0-9]{20,}` which fails to match keys containing `_` or `-` (e.g. `xk_fake_xxx`, `api-key-xxx`). This means API keys with these common characters are not redacted, creating a PII leak.

## Acceptance Criteria

| # | Given | When | Then | Test Name |
|---|-------|------|------|-----------|
| AC1 | An API key value containing underscores (e.g. `xk_fake_abc123def456ghi789`) | The sanitizer processes the string | The key is redacted | `test_api_key_with_underscores_is_redacted` |
| AC2 | An API key value containing dashes (e.g. `api-key-abc123def456ghi789`) | The sanitizer processes the string | The key is redacted | `test_api_key_with_dashes_is_redacted` |
| AC3 | An API key value with mixed underscores and dashes | The sanitizer processes the string | The key is redacted | `test_api_key_with_mixed_separators_is_redacted` |
| AC4 | A short token value (<20 chars) with underscores | The sanitizer processes the string | The value is NOT redacted (no false positive) | `test_short_token_with_separators_not_redacted` |

## Files Affected
- MODIFY: `vigil/processing/sanitizers.py` (api_key regex pattern)
- MODIFY: `tests/unit/test_sanitizers.py` (add new test cases)

## Schema Impact
- [x] No schema changes

## Security Checklist
- [x] S1 Input validation - regex pattern validates correctly
- [x] S3 No secrets in code
- [x] S5 Error messages safe

# Debt Review: Post-Sprint 4

## New Debt Register

| ID | Component | Debt | Impact | Priority |
|----|-----------|------|--------|----------|
| TD-16 | Collector | FastAPI endpoint functions missing return type hints (health.py, agents.py, internal_metrics.py) | OpenAPI spec lacks response schemas | P3 |
| TD-17 | Core | 3 bare `except Exception` blocks silently swallow errors (decorators.py:197, file_storage.py:300, metrics_tracker.py:33) | Hidden failures | P3 |
| TD-18 | All | 31 f-string logging calls (should use lazy % formatting for performance) | Minor perf overhead when log level is disabled | P3 |
| TD-19 | Agent | Magic numbers for byte conversions (1024*1024, 1024**3) in memory.py and disk.py | Readability | P3 |
| TD-20 | Collector | Timestamp normalization duplicated across events.py and metrics.py | DRY violation | P3 |

## Assessment

No P1 or P2 debt was introduced during Sprints 1-4. All items are P3 (low priority, cosmetic or minor performance). The codebase is in good shape for production readiness.

## Recommendation

Defer TD-16 through TD-20 to a future cleanup sprint. Focus remaining effort on Python SDK edge cases and agent integration testing.

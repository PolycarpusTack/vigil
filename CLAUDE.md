# CLAUDE.md

## Project

Vigil — a production-ready audit logging system for Python. Core library + FastAPI collector service + monitoring agent + SDKs (Python, Go, TypeScript).

## Commands

```bash
# Run all tests (691 passing)
PYTHONPATH=. python3 -m pytest tests/ --override-ini="addopts=-v --strict-markers --tb=short" -q

# Run a specific test file
PYTHONPATH=. python3 -m pytest tests/unit/test_engine.py -v --tb=short --override-ini="addopts=-v --strict-markers --tb=short"

# Lint
python3 -m flake8 vigil/ collector/ agent/ sdks/ tests/ --max-line-length=100 --extend-ignore=E402,W503
black --check vigil/ collector/ agent/ tests/
isort --check vigil/ collector/ agent/ tests/

# TypeScript SDK tests
cd sdks/typescript && npx vitest run

# Run collector locally
uvicorn collector.main:app --host 0.0.0.0 --port 8080 --reload

# Docker (full stack)
docker compose up --build -d
```

## Environment Notes

- Use `python3` (no `python` binary)
- Go is not installed; Node.js is available via nvm (v22)
- pytest.ini has coverage addopts that fail without pytest-cov — always use `--override-ini` to bypass
- PYTHONPATH=. is required for imports to resolve

## Architecture

```
vigil/              Core package (engine, events, sanitizers, config, storage)
collector/          FastAPI collector service (event/metric ingestion + querying)
agent/              Server monitoring agent (CPU, memory, disk, network collectors)
sdks/python/        Python SDK client
sdks/go/            Go SDK client
sdks/typescript/    TypeScript SDK client
schema/             JSON Schema definitions (audit_event, metric_event)
tests/              Unit, integration, contract, e2e tests
specs/              Spec files (spec-driven TDD workflow)
config/             Default config files
examples/           Example apps and configs
```

## Key Patterns

- **Package name:** `vigil` (renamed from `audit_framework`)
- **Shared table definition:** `vigil/storage/table_defs.py` — single source of truth for SQL schema used by both core storage and collector models
- **Auth:** Bearer token via SHA-256 hashed API keys; `AUTH_DISABLED=true` env var disables auth for dev
- **Rate limiting:** In-memory sliding window in `collector/middleware/rate_limit.py`
- **PII sanitization:** `PIISanitizer` in `vigil/processing/sanitizers.py` — runs before all storage writes
- **Timestamps:** Always `datetime.now(timezone.utc)` — never `datetime.utcnow()`
- **Config env vars:** `${VAR}` syntax resolved in YAML config files
- **Structured logging:** `collector/logging_config.py` (JSONFormatter, configure_logging)

## Code Style

- **Formatter:** black (line length 100)
- **Import sorting:** isort (black profile)
- **Linter:** flake8 (line length 100, ignore E402 and W503)
- **Type hints:** On all public functions
- **Docstrings:** Google style on public functions
- **Max function length:** 30 lines
- **Max function params:** 4 (use config objects if more)
- **Test naming:** `test_<unit>_<scenario>_<expected_outcome>`
- **Test pattern:** Arrange / Act / Assert

## Testing

- **691 tests, 95.35% coverage**
- Unit tests: `tests/unit/`
- Integration tests: `tests/integration/` (use FastAPI TestClient, not live HTTP)
- Contract tests: `tests/contract/` (validate payloads against JSON Schema)
- E2E: `tests/e2e/test_full_stack.sh` (requires Docker)
- Shared fixtures: `tests/conftest.py` — add new fixtures here, not in test files
- Coverage target: 95%

## Key Files

| File | Purpose |
|------|---------|
| `vigil/core/engine.py` | Central audit engine orchestrator |
| `vigil/core/event.py` | AuditEvent data model |
| `vigil/processing/sanitizers.py` | PII sanitization (passwords, keys, emails, SSNs, cards) |
| `vigil/utils/config.py` | YAML config with env var substitution |
| `vigil/storage/table_defs.py` | Shared SQL table definitions |
| `collector/main.py` | FastAPI app setup and middleware |
| `collector/api/events.py` | Event ingest/query endpoints |
| `collector/auth/api_keys.py` | API key authentication |
| `agent/main.py` | Agent main loop |
| `agent/transport/http_sender.py` | Metric delivery with retry/backoff |
| `tests/conftest.py` | Shared test fixtures |

## Git

- **Repo:** https://github.com/PolycarpusTack/vigil
- **Identity:** PolycarpusTack <yannick.verrydt@outlook.com>
- **Commit style:** Conventional Commits (`feat:`, `fix:`, `test:`, `refactor:`, `docs:`)
- Do not commit files matching .gitignore patterns (*.db, __pycache__, .coverage, etc.)
- Test fixtures use `xk_fake_` prefix for API key patterns (not `sk_live_`/`sk_test_` which trigger GitHub push protection)

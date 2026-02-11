# Vigil

A production-ready audit logging system for Python applications with a collector service, monitoring agent, and multi-language SDKs.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-691%20passed-brightgreen.svg)]()
[![Coverage](https://img.shields.io/badge/coverage-95.35%25-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Architecture

```
                    +-----------+     +-----------+     +-----------+
                    | Python SDK|     |  Go SDK   |     |  TS SDK   |
                    +-----+-----+     +-----+-----+     +-----+-----+
                          |                 |                 |
                          v                 v                 v
                    +-------------------------------------------+
                    |           Collector (FastAPI)              |
                    |  /api/v1/events  /api/v1/metrics  /health |
                    +---------------------+---------------------+
                                          |
                    +---------------------+---------------------+
                    |              Vigil Core                    |
                    |  AuditEngine > PII Sanitizer > Storage    |
                    +---------------------+---------------------+
                                          |
                          +---------------+---------------+
                          |               |               |
                    +-----+-----+   +-----+-----+   +----+----+
                    |   File    |   |    SQL    |   |  Cloud  |
                    |  Storage  |   |  Storage  |   | Storage |
                    +-----------+   +-----------+   +---------+

   +----------------+
   | Monitoring     |  CPU, memory, disk, network, process metrics
   | Agent          |-----> POST /api/v1/metrics
   +----------------+
```

**Components:**

| Component | Path | Description |
|-----------|------|-------------|
| Core | `vigil/` | Audit engine, events, PII sanitizer, config, storage backends |
| Collector | `collector/` | FastAPI service — event ingestion, querying, agent metrics |
| Agent | `agent/` | Server monitoring agent with pluggable collectors |
| Python SDK | `sdks/python/` | Client library for sending events to the collector |
| Go SDK | `sdks/go/` | Go client with validation |
| TypeScript SDK | `sdks/typescript/` | TypeScript client with type safety |
| Schemas | `schema/` | JSON Schema definitions for events and metrics |

## Quick Start

### Core Library

```python
from vigil import audit_log, AuditEngine, AuditContext

# Decorator — automatically logs timing, parameters, exceptions
@audit_log
def process_payment(amount, user_id):
    return charge_card(amount, user_id)

# Context manager
with AuditContext(action="FILE_UPLOAD", resource_type="file"):
    file.save("document.pdf")

# Direct API
audit = AuditEngine()
audit.log(
    action="USER_LOGIN",
    actor={"username": "john"},
    result={"status": "SUCCESS"},
)
```

### Collector Service

```bash
# With Docker Compose (collector + postgres + agent)
docker compose up --build -d

# Or run locally
pip install -r collector/requirements.txt
uvicorn collector.main:app --host 0.0.0.0 --port 8080 --reload
```

### Send Events via SDK

```python
from audit_sdk import AuditClient

client = AuditClient(
    base_url="http://localhost:8080",
    api_key="your-api-key",
)
client.log("USER_LOGIN", actor={"username": "john"})
```

## Configuration

```yaml
# config/audit.yaml
vigil:
  core:
    enabled: true
    application_name: "my_app"
    environment: "production"

  storage:
    backends:
      - type: file
        directory: ./logs/audit
        format: json

  processing:
    sanitization:
      enabled: true
```

```python
from vigil import AuditEngine

audit = AuditEngine(config_file="config/audit.yaml")
```

Environment variable substitution is supported with `${VAR}` syntax in YAML values.

## Security

**PII sanitization** is built in. Sensitive fields are automatically redacted before storage:

- Passwords, secrets, tokens, API keys (including keys with `_` and `-`)
- Credit card numbers, SSNs
- Email addresses
- Custom patterns via configuration

**Authentication:** Bearer token with SHA-256 hashed keys. Set `AUTH_DISABLED=true` for development only.

**Rate limiting:** In-memory sliding window per API key on all collector endpoints.

## Development

### Setup

```bash
git clone https://github.com/PolycarpusTack/vigil.git
cd vigil
pip install -e ".[dev,database,web]"
pip install -r collector/requirements.txt
pip install -r requirements-dev.txt
```

### Test

```bash
# All tests (691 passing, 95.35% coverage)
PYTHONPATH=. python3 -m pytest tests/ --override-ini="addopts=-v --strict-markers --tb=short" -q

# Unit only
PYTHONPATH=. python3 -m pytest tests/unit/ -v --override-ini="addopts=-v --strict-markers --tb=short"

# TypeScript SDK
cd sdks/typescript && npx vitest run
```

### Lint

```bash
black vigil/ collector/ agent/ tests/
isort vigil/ collector/ agent/ tests/
flake8 vigil/ collector/ agent/ sdks/ tests/ --max-line-length=100
```

### Docker

```bash
docker compose up --build -d    # Start all services
docker compose logs -f           # Tail logs
docker compose down              # Stop
```

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/v1/events` | Yes | Ingest audit event |
| `POST` | `/api/v1/events/batch` | Yes | Ingest batch of events |
| `GET` | `/api/v1/events/{id}` | Yes | Get event by ID |
| `GET` | `/api/v1/events` | Yes | Query events |
| `POST` | `/api/v1/metrics` | Yes | Ingest agent metrics |
| `GET` | `/api/v1/metrics` | Yes | Query metrics |
| `POST` | `/api/v1/agents/register` | Yes | Register monitoring agent |
| `GET` | `/api/v1/agents` | Yes | List registered agents |
| `GET` | `/health` | No | Health check |
| `GET` | `/internal/metrics` | No | Internal collector metrics |

## Project Status

- **Version:** 1.0.0
- **Tests:** 691 passed
- **Coverage:** 95.35%
- **Lint:** Clean (black, isort, flake8)
- **Python:** 3.8+
- **License:** MIT

## License

MIT

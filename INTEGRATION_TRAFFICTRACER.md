# 🔌 Integrating Vigil with TrafficTracer

**How to integrate the standalone vigil module into TrafficTracer**

---

## 📦 Module Status

The `vigil` is being developed as a **completely independent Python package** in:
```
/mnt/c/Projects/vigil/
```

This allows:
- ✅ Independent development and testing
- ✅ Version control separate from TrafficTracer
- ✅ Reusable across multiple projects
- ✅ Easy to update without affecting TrafficTracer
- ✅ Can be pip-installed or bundled

---

## 🚀 Integration Methods

### Method 1: Install as Package (Recommended for Production)

Once the framework is complete and tested:

```bash
# Option A: Install from PyPI (when published)
pip install vigil

# Option B: Install from local directory
cd /mnt/c/Projects/vigil
pip install -e .

# Option C: Install specific version
pip install vigil==1.0.0
```

Then in TrafficTracer:
```python
# Just import and use
from vigil import audit_log, AuditEngine

@audit_log
def execute_query(sql, params):
    return conn.execute(sql, params)
```

### Method 2: Bundle with TrafficTracer (Recommended for Development)

Copy the module into TrafficTracer when ready:

```bash
# Copy the entire module
cp -r /mnt/c/Projects/vigil/vigil /mnt/c/Projects/traffictracer/

# Now it's part of TrafficTracer
```

Update TrafficTracer's `requirements.txt`:
```
# Add Vigil dependencies
pyyaml>=6.0
python-dateutil>=2.8.0
```

### Method 3: Git Submodule (Recommended for Linked Development)

Keep them linked during development:

```bash
cd /mnt/c/Projects/traffictracer
git submodule add /mnt/c/Projects/vigil vigil
```

---

## 📋 TrafficTracer Integration Plan

### Phase 1: Hook Points Identified

These are the key places in TrafficTracer where we'll add audit logging:

#### 1. Database Operations (`core/db_connector.py`)

```python
# Before (current code)
def execute_query(self, query, params=None):
    cursor = self.connection.cursor()
    cursor.execute(query, params)
    return cursor.fetchall()

# After (with Vigil)
from vigil import audit_log

@audit_log(
    category="DATABASE",
    action_type="QUERY_EXECUTION",
    capture_params=True,
    capture_result_count=True
)
def execute_query(self, query, params=None):
    cursor = self.connection.cursor()
    cursor.execute(query, params)
    return cursor.fetchall()
```

#### 2. API Endpoints (`api/server_secure.py`)

```python
# Before (current code)
@app.post("/api/v1/query/execute")
async def execute_query(request: QueryRequest):
    result = execute_sql(request.sql, request.params)
    return {"result": result}

# After (with Vigil)
from vigil.integrations import FastAPIAuditMiddleware

# Add middleware (audits ALL endpoints automatically)
app.add_middleware(FastAPIAuditMiddleware)

# Or per-endpoint
@app.post("/api/v1/query/execute")
@audit_log(category="API", resource="query/execute")
async def execute_query(request: QueryRequest):
    result = execute_sql(request.sql, request.params)
    return {"result": result}
```

#### 3. Authentication (`api/authentication_secure.py`)

```python
# Before
def login(username, password):
    user = authenticate(username, password)
    return create_session(user)

# After
from vigil import audit_log

@audit_log(
    action_type="LOGIN",
    category="AUTHENTICATION",
    capture_exceptions=True,
    security_event=True
)
def login(username, password):
    user = authenticate(username, password)
    return create_session(user)
```

#### 4. Connection Management (`core/connection_manager.py`)

```python
# Before
def create_connection(self, connection_info):
    conn = self._establish_connection(connection_info)
    return conn

# After
from vigil import AuditContext

def create_connection(self, connection_info):
    with AuditContext(
        action="CONNECTION_CREATE",
        category="DATABASE",
        resource=connection_info['database']
    ):
        conn = self._establish_connection(connection_info)
        return conn
```

#### 5. GUI Actions (`ui/main_window_orchestrator.py`)

```python
# Before
def on_export_click(self):
    self.export_to_excel()

# After
from vigil import audit_log

@audit_log(
    action_type="EXPORT",
    category="UI_ACTION",
    resource_type="excel"
)
def on_export_click(self):
    self.export_to_excel()
```

---

## ⚙️ TrafficTracer Configuration

Create `config/audit.yaml` in TrafficTracer:

```yaml
vigil:
  core:
    enabled: true
    application_name: "traffictracer"
    version: "2.0.0"
    environment: "production"  # or "development"

  storage:
    backends:
      # Primary: File storage
      - type: file
        enabled: true
        directory: ./logs/audit
        format: json
        filename_pattern: "traffictracer_audit_{category}_{date}.log"
        rotation:
          enabled: true
          when: midnight
          backup_count: 90
          compress: true
          compress_after_days: 7

      # Secondary: Database storage (optional)
      - type: database
        enabled: false  # Enable when ready
        connection:
          # Use same database as TrafficTracer
          dialect: "${DB_TYPE}"
          host: "${DB_HOST}"
          port: "${DB_PORT}"
          database: "${DB_NAME}"
          username: "${DB_USER}"
          password: "${DB_PASSWORD}"
        table_name: "traffictracer_audit_events"

  processing:
    # PII Sanitization
    sanitization:
      enabled: true
      redact_patterns:
        - password
        - credit_card
        - ssn
        - email  # partial redaction

    # Event filtering
    filters:
      - type: severity
        levels: ["INFO", "WARNING", "ERROR", "CRITICAL"]

      - type: category
        include: ["DATABASE", "API", "AUTH", "SECURITY"]
        exclude: ["HEARTBEAT"]

  performance:
    # Async processing (non-blocking)
    async:
      enabled: true
      worker_threads: 2
      queue_size: 5000

    # Batching for performance
    batching:
      enabled: true
      batch_size: 50
      batch_timeout_seconds: 5

  compliance:
    # GDPR compliance
    gdpr:
      enabled: true
      retention_days: 90
      auto_delete_after_retention: true

  security:
    # Encryption (optional)
    encryption:
      enabled: false

    # Signing for tamper detection (optional)
    signing:
      enabled: false
```

---

## 🎯 Integration Steps (When Framework is Ready)

### Step 1: Install the Framework

```bash
cd /mnt/c/Projects/vigil
pip install -e .
```

### Step 2: Add Configuration to TrafficTracer

```bash
cd /mnt/c/Projects/traffictracer
mkdir -p config
# Copy audit.yaml from above
```

### Step 3: Initialize Vigil in TrafficTracer

Create `traffictracer/audit_init.py`:

```python
"""Initialize Vigil for TrafficTracer."""

from vigil import AuditEngine, get_default_engine
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Global audit engine instance
_audit_engine = None


def initialize_audit(config_file: str = None):
    """Initialize the Vigil for TrafficTracer."""
    global _audit_engine

    if config_file is None:
        # Try to find default config
        config_file = Path(__file__).parent.parent / "config" / "audit.yaml"
        if not config_file.exists():
            logger.warning("Audit config not found, using defaults")
            config_file = None

    try:
        _audit_engine = AuditEngine(config_file=str(config_file) if config_file else None)
        logger.info("Vigil initialized successfully")
        return _audit_engine
    except Exception as e:
        logger.error(f"Failed to initialize Vigil: {e}")
        # Fallback to default (file-only, minimal)
        _audit_engine = AuditEngine()
        return _audit_engine


def get_audit_engine():
    """Get the global audit engine instance."""
    global _audit_engine
    if _audit_engine is None:
        return initialize_audit()
    return _audit_engine


# Convenience function for quick logging
def log_audit_event(action: str, **kwargs):
    """Log an audit event."""
    engine = get_audit_engine()
    return engine.log(action=action, **kwargs)
```

### Step 4: Initialize at Application Startup

In `unified_traffictracer.py` or `main_*.py`:

```python
from traffictracer.audit_init import initialize_audit

def main():
    # Initialize Vigil early
    try:
        audit = initialize_audit()
        audit.log(
            action="APPLICATION_STARTUP",
            category="SYSTEM",
            metadata={"version": "2.0.0"}
        )
    except Exception as e:
        print(f"Warning: Vigil initialization failed: {e}")
        # Continue without audit logging

    # Rest of application startup...
```

### Step 5: Add Decorators to Key Functions

```python
# In core/db_connector.py
from vigil import audit_log

class DatabaseConnector:
    @audit_log(category="DATABASE", action_type="QUERY")
    def execute_query(self, sql, params=None):
        # existing code...

    @audit_log(category="DATABASE", action_type="CONNECTION")
    def create_connection(self, connection_info):
        # existing code...
```

### Step 6: Add Middleware to API Server

```python
# In api/server_secure.py
from fastapi import FastAPI
from vigil.integrations import FastAPIAuditMiddleware

app = FastAPI()

# Add audit middleware (automatically logs all requests)
app.add_middleware(FastAPIAuditMiddleware)
```

### Step 7: Test the Integration

```python
# test_audit_integration.py
from traffictracer.audit_init import get_audit_engine
from vigil import AuditQuery

def test_audit_logging():
    """Test that audit events are being logged."""
    audit = get_audit_engine()

    # Log a test event
    audit.log(action="TEST_EVENT", category="TEST")

    # Query recent events
    events = AuditQuery.search(
        time_range="last_1h",
        category="TEST"
    )

    assert len(events) > 0
    print(f"✅ Audit logging is working: {len(events)} events found")

if __name__ == "__main__":
    test_audit_logging()
```

---

## 🔍 Viewing Audit Logs

### Option 1: File Logs

```bash
# View today's audit logs
cat logs/audit/traffictracer_audit_database_2025-10-10.log | jq

# Search for specific user
cat logs/audit/*.log | jq 'select(.actor.username == "yannick.verrydt")'

# Count events by category
cat logs/audit/*.log | jq -r '.action.category' | sort | uniq -c
```

### Option 2: Query API (Future)

```python
from vigil import AuditQuery

# Search for failed logins
events = AuditQuery.search(
    query="action.type:LOGIN AND result.status:FAILURE",
    time_range="last_24h"
)

# Export to Excel
AuditQuery.export(
    format="excel",
    filename="security_audit.xlsx",
    filters={"category": "SECURITY"}
)
```

### Option 3: Add to TrafficTracer GUI (Future Enhancement)

```python
# ui/audit_viewer_panel.py
class AuditViewerPanel(tk.Frame):
    """Panel to view audit logs within TrafficTracer."""

    def __init__(self, parent):
        super().__init__(parent)
        self.create_widgets()

    def create_widgets(self):
        # Tree view for events
        self.tree = ttk.Treeview(self, columns=("timestamp", "user", "action"))
        # ... populate from AuditQuery
```

---

## 📊 Monitoring Integration

### Add Audit Metrics to Existing Metrics Endpoint

In `api/server_secure.py`:

```python
@app.get("/api/v1/metrics/info")
async def get_metrics_info():
    """Get observability and metrics information."""

    # Existing metrics...
    info = {
        "timestamp": datetime.now().isoformat(),
        "monitoring_enabled": settings.monitoring.enabled,
        # ... existing fields
    }

    # Add audit metrics
    try:
        from traffictracer.audit_init import get_audit_engine
        audit = get_audit_engine()

        info["audit"] = {
            "enabled": True,
            "events_logged_today": audit.get_event_count(time_range="today"),
            "storage_backends": audit.get_active_backends(),
            "last_event_time": audit.get_last_event_time(),
        }
    except Exception as e:
        info["audit"] = {"enabled": False, "error": str(e)}

    return info
```

---

## 🧪 Testing Plan

### Unit Tests

```python
# tests/test_audit_integration.py
def test_audit_decorator_on_query():
    """Test that @audit_log decorator works on database queries."""
    from core.db_connector import DatabaseConnector

    # Execute query
    connector = DatabaseConnector()
    result = connector.execute_query("SELECT 1")

    # Verify audit event was created
    audit = get_audit_engine()
    last_event = audit.get_last_event()

    assert last_event.action.category == "DATABASE"
    assert last_event.action.type == "QUERY"
```

### Integration Tests

```python
def test_api_audit_middleware():
    """Test that API requests are audited."""
    from fastapi.testclient import TestClient
    from api.server_secure import app

    client = TestClient(app)
    response = client.get("/api/v1/health")

    # Verify audit event
    audit = get_audit_engine()
    last_event = audit.get_last_event()

    assert last_event.action.category == "API"
    assert last_event.action.resource.path == "/api/v1/health"
```

---

## 🛡️ Security Considerations

### Configuration Security

```yaml
# Use environment variables for sensitive data
vigil:
  storage:
    backends:
      - type: database
        connection:
          password: "${AUDIT_DB_PASSWORD}"  # From environment

  security:
    signing:
      secret_key: "${AUDIT_SIGNING_KEY}"  # From environment
```

### Separate Audit Database (Recommended)

For maximum security, use a separate database for audit logs:

```yaml
storage:
  backends:
    - type: database
      connection:
        host: "audit-db.internal"  # Separate server
        database: "audit_logs"
        username: "audit_writer"  # Limited permissions
```

---

## 📈 Rollout Strategy

### Phase 1: Development Environment (Week 1)

- ✅ Install Vigil in dev
- ✅ Add to 2-3 key functions as POC
- ✅ Verify logs are being created
- ✅ Test performance impact

### Phase 2: Staging Environment (Week 2)

- ✅ Deploy to staging
- ✅ Add decorators to all database operations
- ✅ Add API middleware
- ✅ Monitor for 1 week

### Phase 3: Production (Week 3)

- ✅ Deploy to production
- ✅ Start with file-only storage
- ✅ Monitor performance
- ✅ Gradually enable more features

### Phase 4: Full Features (Week 4+)

- ✅ Enable database storage
- ✅ Add compliance features
- ✅ Create audit dashboards
- ✅ Train team on audit queries

---

## 🚨 Rollback Plan

If issues arise:

```python
# Option 1: Disable via config
vigil:
  core:
    enabled: false  # Turns off all auditing

# Option 2: Remove decorators
# Just comment out @audit_log decorators
# @audit_log  # Temporarily disabled
def my_function():
    pass

# Option 3: Uninstall
pip uninstall vigil
# Code will fail gracefully if framework is missing
```

---

## ✅ Success Criteria

The integration is successful when:

- ✅ All database queries are logged
- ✅ All API requests are logged
- ✅ Authentication events are logged
- ✅ Performance impact < 5%
- ✅ Logs are queryable
- ✅ No application errors
- ✅ Compliance requirements met

---

## 📞 Support During Integration

**Questions or Issues:**
1. Check `/mnt/c/Projects/vigil/docs/` for detailed documentation
2. Review examples in `/mnt/c/Projects/vigil/examples/`
3. Run tests: `pytest /mnt/c/Projects/vigil/tests/`

---

## 🎯 Next Steps

**Once the Vigil is complete:**

1. **Review** this integration plan
2. **Test** in development environment first
3. **Gradually enable** features
4. **Monitor** performance and logs
5. **Iterate** based on feedback

The framework is designed to be **low-risk** and **easy to integrate** - you can start with minimal features and add more as needed!

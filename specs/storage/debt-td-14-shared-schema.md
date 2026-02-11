# Spec: Extract Shared Audit Events Table Definition
- component: storage
- status: done
- priority: P2-medium
- depends-on: []
- debt-tag: DEBT:TD-14 sql_storage.py and collector/models/event_model.py define same table independently

## Problem
`vigil/storage/sql_storage.py` and `collector/models/event_model.py` each define the `audit_events` table independently. Changes to one won't propagate to the other, creating schema drift risk. The table definition should be extracted to a single source of truth.

## Acceptance Criteria

| # | Given | When | Then | Test Name |
|---|-------|------|------|-----------|
| AC1 | A shared table builder exists | Both sql_storage and collector import it | They produce identical column definitions | `test_shared_table_columns_match` |
| AC2 | SQLStorageBackend uses the shared builder | Backend is initialized | The audit_events table is created correctly | existing `test_init_creates_table` |
| AC3 | Collector event_model uses the shared builder | Collector init_db is called | The audit_events table is created correctly | existing collector integration tests |

## Files Affected
- CREATE: `vigil/storage/table_defs.py` (single source of truth for table definition)
- MODIFY: `vigil/storage/sql_storage.py` (import from table_defs)
- MODIFY: `collector/models/event_model.py` (import from table_defs)

## Security Checklist
- [x] S1 Input validation

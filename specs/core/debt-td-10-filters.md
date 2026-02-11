# Spec: Implement Event Filter Chain
- component: core
- status: done
- priority: P3-low
- depends-on: []
- debt-tag: DEBT:TD-10 engine.py TODO: Apply filters with no implementation

## Problem
`engine.py:_process_event()` has a `# TODO: Apply filters` placeholder. The config already supports a `processing.filters` list but no filter logic exists. Events should be filterable by category and action type via configuration.

## Acceptance Criteria

| # | Given | When | Then | Test Name |
|---|-------|------|------|-----------|
| AC1 | A filter excludes category DATABASE | A DATABASE event is logged | The event is dropped (returns None) | `test_filter_by_category_excludes_event` |
| AC2 | A filter includes only category API | An API event is logged | The event passes through | `test_filter_by_category_allows_event` |
| AC3 | A filter excludes action_type DELETE | A DELETE event is logged | The event is dropped | `test_filter_by_action_type_excludes_event` |
| AC4 | Multiple filters are configured | Events are logged | All filters are applied in sequence | `test_filter_chain_applies_all_filters` |
| AC5 | No filters are configured | Events are logged | All events pass through | `test_no_filters_allows_all_events` |

## Filter Config Format
```yaml
processing:
  filters:
    - type: exclude_category
      categories: [DATABASE, SYSTEM]
    - type: exclude_action_type
      action_types: [DELETE]
```

## Files Affected
- MODIFY: `vigil/core/engine.py` (implement filter logic in _process_event)
- MODIFY: `tests/unit/test_engine.py` (add filter chain tests)

## Security Checklist
- [x] S1 Input validation

# Spec: Structured Logging
- component: collector
- status: done
- priority: P2-medium
- depends-on: []
- debt-tag: none

## Problem
The collector uses Python's default text-based log formatting. In production, logs need to be machine-parseable JSON for aggregation in tools like ELK/Loki. There is no structured format option.

## Acceptance Criteria

| # | Given | When | Then | Test Name |
|---|-------|------|------|-----------|
| AC1 | LOG_FORMAT=json | Collector logs a message | Output is valid JSON with timestamp, level, message, logger fields | `test_json_log_formatter_output` |
| AC2 | LOG_FORMAT=json | A request is processed | The log entry includes the expected fields | `test_json_log_formatter_fields` |
| AC3 | LOG_FORMAT=text (default) | Collector logs a message | Output is plain text (unchanged) | `test_text_log_formatter_default` |
| AC4 | JSON formatter is used | An exception is logged | exc_info is included in JSON | `test_json_log_formatter_exception` |

## Files Affected
- CREATE: `collector/logging_config.py`
- MODIFY: `collector/config.py` (add log_format field)
- MODIFY: `collector/main.py` (use structured logging setup)
- CREATE: `tests/unit/test_collector_logging.py`

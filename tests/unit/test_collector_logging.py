"""Unit tests for collector structured logging.

Tests cover:
- JSON log formatter output format
- Required fields in JSON output
- Default text formatter unchanged
- Exception info in JSON logs
"""

import json
import logging

from collector.logging_config import JSONFormatter


class TestJSONLogFormatter:
    """Tests for JSON structured log formatter."""

    def test_json_log_formatter_output(self):
        """JSON formatter produces valid JSON."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=None,
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_json_log_formatter_fields(self):
        """JSON output includes timestamp, level, message, logger."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="collector.api.events",
            level=logging.WARNING,
            pathname="events.py",
            lineno=42,
            msg="Something happened",
            args=None,
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed["level"] == "WARNING"
        assert parsed["message"] == "Something happened"
        assert parsed["logger"] == "collector.api.events"
        assert "timestamp" in parsed

    def test_text_log_formatter_default(self):
        """Default text formatter produces non-JSON output."""
        formatter = logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Hello",
            args=None,
            exc_info=None,
        )
        output = formatter.format(record)
        # Should NOT be valid JSON
        try:
            json.loads(output)
            is_json = True
        except json.JSONDecodeError:
            is_json = False
        assert not is_json

    def test_json_log_formatter_exception(self):
        """JSON formatter includes exception info when present."""
        formatter = JSONFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=None,
            exc_info=exc_info,
        )
        output = formatter.format(record)
        parsed = json.loads(output)

        assert "exception" in parsed
        assert "ValueError" in parsed["exception"]
        assert "test error" in parsed["exception"]

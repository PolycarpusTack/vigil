"""Unit tests for AuditContext context manager.

Tests cover:
- Basic context manager usage (enter/exit)
- Timing and performance tracking
- Exception capture
- Success/failure marking
- Resource info
- Metadata addition
- repr
"""

from unittest.mock import MagicMock, patch

from vigil.core.context import AuditContext


class TestAuditContextBasic:
    """Tests for basic AuditContext behavior."""

    def test_enter_returns_self(self):
        """__enter__ returns the context instance."""
        engine = MagicMock()
        ctx = AuditContext(action="test_op", engine=engine)
        result = ctx.__enter__()
        assert result is ctx

    def test_enter_sets_start_time(self):
        """__enter__ sets start_time."""
        engine = MagicMock()
        ctx = AuditContext(action="test_op", engine=engine)
        assert ctx.start_time is None
        ctx.__enter__()
        assert ctx.start_time is not None

    def test_exit_logs_event(self):
        """__exit__ calls engine.log()."""
        engine = MagicMock()
        ctx = AuditContext(action="test_op", engine=engine)
        ctx.__enter__()
        ctx.__exit__(None, None, None)
        engine.log.assert_called_once()

    def test_exit_sets_duration(self):
        """__exit__ sets duration_ms."""
        engine = MagicMock()
        ctx = AuditContext(action="test_op", engine=engine)
        ctx.__enter__()
        ctx.__exit__(None, None, None)
        assert ctx.duration_ms is not None
        assert ctx.duration_ms >= 0

    def test_context_manager_protocol(self):
        """Works with 'with' statement."""
        engine = MagicMock()
        with AuditContext(action="test_op", engine=engine) as ctx:
            assert ctx.start_time is not None
        engine.log.assert_called_once()

    def test_default_result_status_is_success(self):
        """Default result status is SUCCESS."""
        engine = MagicMock()
        with AuditContext(action="test_op", engine=engine):
            pass
        call_kwargs = engine.log.call_args[1]
        assert call_kwargs["result"]["status"] == "SUCCESS"


class TestAuditContextExceptions:
    """Tests for exception handling."""

    def test_exception_sets_failure_status(self):
        """Exception sets result_status to FAILURE."""
        engine = MagicMock()
        try:
            with AuditContext(action="test_op", engine=engine):
                raise ValueError("test error")
        except ValueError:
            pass
        call_kwargs = engine.log.call_args[1]
        assert call_kwargs["result"]["status"] == "FAILURE"

    def test_exception_captured_in_error(self):
        """Exception info is captured in error dict."""
        engine = MagicMock()
        try:
            with AuditContext(action="test_op", engine=engine):
                raise ValueError("boom")
        except ValueError:
            pass
        call_kwargs = engine.log.call_args[1]
        assert call_kwargs["error"]["occurred"] is True
        assert call_kwargs["error"]["type"] == "ValueError"
        assert "boom" in call_kwargs["error"]["message"]

    def test_exception_not_suppressed(self):
        """Exceptions are re-raised (not suppressed)."""
        engine = MagicMock()
        raised = False
        try:
            with AuditContext(action="test_op", engine=engine):
                raise RuntimeError("should propagate")
        except RuntimeError:
            raised = True
        assert raised

    def test_capture_exceptions_false_skips_error(self):
        """capture_exceptions=False still sets FAILURE but no error dict."""
        engine = MagicMock()
        try:
            with AuditContext(action="test_op", engine=engine, capture_exceptions=False):
                raise ValueError("no capture")
        except ValueError:
            pass
        call_kwargs = engine.log.call_args[1]
        assert call_kwargs["error"] is None
        assert call_kwargs["result"]["status"] == "FAILURE"


class TestAuditContextMethods:
    """Tests for success/failure/add_metadata methods."""

    def test_success_sets_status(self):
        """success() sets status to SUCCESS with message."""
        engine = MagicMock()
        with AuditContext(action="test_op", engine=engine) as ctx:
            ctx.success("all good")
        call_kwargs = engine.log.call_args[1]
        assert call_kwargs["result"]["status"] == "SUCCESS"
        assert call_kwargs["result"]["message"] == "all good"

    def test_failure_sets_status(self):
        """failure() sets status to FAILURE with message."""
        engine = MagicMock()
        with AuditContext(action="test_op", engine=engine) as ctx:
            ctx.failure("went wrong")
        call_kwargs = engine.log.call_args[1]
        assert call_kwargs["result"]["status"] == "FAILURE"

    def test_failure_with_exception(self):
        """failure() can attach an exception."""
        engine = MagicMock()
        exc = ValueError("manual error")
        with AuditContext(action="test_op", engine=engine) as ctx:
            ctx.failure("oops", exception=exc)
        call_kwargs = engine.log.call_args[1]
        assert call_kwargs["error"]["type"] == "ValueError"

    def test_add_metadata(self):
        """add_metadata() adds key/value to custom metadata."""
        engine = MagicMock()
        with AuditContext(action="test_op", engine=engine) as ctx:
            ctx.add_metadata("user_id", "123")
        call_kwargs = engine.log.call_args[1]
        assert "user_id" in call_kwargs["custom"]
        assert call_kwargs["custom"]["user_id"] == "123"

    def test_repr(self):
        """repr includes action and category."""
        engine = MagicMock()
        ctx = AuditContext(action="my_action", category="API", engine=engine)
        r = repr(ctx)
        assert "my_action" in r
        assert "API" in r


class TestAuditContextResource:
    """Tests for resource info."""

    def test_resource_type_and_name(self):
        """Resource info is included in custom field."""
        engine = MagicMock()
        with AuditContext(
            action="query",
            engine=engine,
            resource_type="table",
            resource_name="users",
        ):
            pass
        call_kwargs = engine.log.call_args[1]
        resource = call_kwargs["custom"]["resource"]
        assert resource["type"] == "table"
        assert resource["name"] == "users"

    def test_no_resource(self):
        """Empty resource when not specified."""
        engine = MagicMock()
        with AuditContext(action="op", engine=engine):
            pass
        call_kwargs = engine.log.call_args[1]
        assert call_kwargs["custom"]["resource"] == {}


class TestAuditContextEngine:
    """Tests for engine resolution."""

    def test_uses_provided_engine(self):
        """Uses engine when explicitly provided."""
        engine = MagicMock()
        ctx = AuditContext(action="op", engine=engine)
        assert ctx.engine is engine

    @patch("vigil.get_default_engine")
    def test_uses_default_engine_when_none(self, mock_get_default):
        """Falls back to default engine when none provided."""
        mock_engine = MagicMock()
        mock_get_default.return_value = mock_engine
        ctx = AuditContext(action="op")
        assert ctx.engine is mock_engine

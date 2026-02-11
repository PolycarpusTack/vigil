"""Unit tests for audit logging decorators.

Tests cover:
- Depth limiting in _serialize_value (max_depth=5)
- Parameter capture
- Exception handling
- Return value capture
- Performance metrics
- Edge cases
"""

import time

import pytest

from vigil.core.decorators import _serialize_value, audit_log
from vigil.core.engine import AuditEngine
from vigil.utils.config import AuditConfig


class TestSerializeValue:
    """Test suite for _serialize_value function."""

    def test_serialize_none(self):
        """Test serialization of None value."""
        result = _serialize_value(None)
        assert result is None

    def test_serialize_boolean(self):
        """Test serialization of boolean values."""
        assert _serialize_value(True) is True
        assert _serialize_value(False) is False

    def test_serialize_integer(self):
        """Test serialization of integer values."""
        assert _serialize_value(42) == 42
        assert _serialize_value(0) == 0
        assert _serialize_value(-100) == -100

    def test_serialize_float(self):
        """Test serialization of float values."""
        assert _serialize_value(3.14) == 3.14
        assert _serialize_value(0.0) == 0.0
        assert _serialize_value(-2.5) == -2.5

    def test_serialize_string(self):
        """Test serialization of string values."""
        assert _serialize_value("hello") == "hello"
        assert _serialize_value("") == ""

    def test_serialize_long_string(self):
        """Test that long strings are truncated."""
        long_string = "a" * 1500
        result = _serialize_value(long_string, max_length=1000)
        assert len(result) <= 1020  # 1000 + "... (truncated)"
        assert result.endswith("... (truncated)")

    def test_serialize_string_exact_max_length(self):
        """Test string at exact max length is not truncated."""
        string = "a" * 1000
        result = _serialize_value(string, max_length=1000)
        assert result == string
        assert "truncated" not in result

    def test_serialize_list(self):
        """Test serialization of lists."""
        result = _serialize_value([1, 2, 3])
        assert result == [1, 2, 3]

    def test_serialize_large_list(self):
        """Test that large lists are summarized."""
        large_list = list(range(100))
        result = _serialize_value(large_list)
        assert isinstance(result, str)
        assert "list with 100 items" in result

    def test_serialize_list_exactly_10_items(self):
        """Test list with exactly 10 items is serialized."""
        ten_items = list(range(10))
        result = _serialize_value(ten_items)
        assert isinstance(result, list)
        assert len(result) == 10

    def test_serialize_list_11_items(self):
        """Test list with 11 items is summarized."""
        eleven_items = list(range(11))
        result = _serialize_value(eleven_items)
        assert isinstance(result, str)
        assert "list with 11 items" in result

    def test_serialize_tuple(self):
        """Test serialization of tuples."""
        result = _serialize_value((1, 2, 3))
        assert result == [1, 2, 3]  # Converted to list

    def test_serialize_large_tuple(self):
        """Test that large tuples are summarized."""
        large_tuple = tuple(range(100))
        result = _serialize_value(large_tuple)
        assert isinstance(result, str)
        assert "tuple with 100 items" in result

    def test_serialize_dict(self):
        """Test serialization of dictionaries."""
        result = _serialize_value({"a": 1, "b": 2})
        assert result == {"a": 1, "b": 2}

    def test_serialize_large_dict(self):
        """Test that large dicts are summarized."""
        large_dict = {f"key_{i}": i for i in range(100)}
        result = _serialize_value(large_dict)
        assert isinstance(result, str)
        assert "dict with 100 keys" in result

    def test_serialize_dict_exactly_20_keys(self):
        """Test dict with exactly 20 keys is serialized."""
        twenty_keys = {f"key_{i}": i for i in range(20)}
        result = _serialize_value(twenty_keys)
        assert isinstance(result, dict)
        assert len(result) == 20

    def test_serialize_dict_21_keys(self):
        """Test dict with 21 keys is summarized."""
        twenty_one_keys = {f"key_{i}": i for i in range(21)}
        result = _serialize_value(twenty_one_keys)
        assert isinstance(result, str)
        assert "dict with 21 keys" in result

    def test_serialize_nested_dict(self):
        """Test serialization of nested dictionaries."""
        nested = {"outer": {"inner": {"deep": "value"}}}
        result = _serialize_value(nested)
        assert result == nested

    def test_serialize_nested_list(self):
        """Test serialization of nested lists."""
        nested = [[1, 2], [3, 4]]
        result = _serialize_value(nested)
        assert result == nested

    def test_serialize_max_depth_limit(self):
        """Test that max depth limit prevents deep recursion."""
        # Create deeply nested structure
        deep = {"level": 0}
        current = deep
        for i in range(10):
            current["nested"] = {"level": i + 1}
            current = current["nested"]

        result = _serialize_value(deep, max_depth=5)
        # Should contain depth limit message at level 6
        assert "<max depth 5 exceeded>" in str(result)

    def test_serialize_depth_exactly_at_limit(self):
        """Test serialization at exactly max depth."""
        # Create structure with depth exactly 5
        deep = {"l1": {"l2": {"l3": {"l4": {"l5": "value"}}}}}
        result = _serialize_value(deep, max_depth=5)
        # Should be serialized without depth exceeded message
        assert "<max depth" not in str(result)

    def test_serialize_depth_one_over_limit(self):
        """Test serialization just over max depth."""
        # Create structure with depth 6
        deep = {"l1": {"l2": {"l3": {"l4": {"l5": {"l6": "value"}}}}}}
        result = _serialize_value(deep, max_depth=5)
        # Should contain depth exceeded message
        assert "<max depth 5 exceeded>" in str(result)

    def test_serialize_custom_max_depth(self):
        """Test custom max_depth parameter."""
        deep = {"a": {"b": {"c": "value"}}}
        result = _serialize_value(deep, max_depth=2)
        assert "<max depth 2 exceeded>" in str(result)

    def test_serialize_object_with_dict(self):
        """Test serialization of objects with __dict__."""

        class CustomObject:
            def __init__(self):
                self.value = 42

        obj = CustomObject()
        result = _serialize_value(obj)
        assert isinstance(result, str)
        assert "CustomObject object" in result

    def test_serialize_object_without_dict(self):
        """Test serialization of objects without __dict__."""
        # Built-in types like int don't have __dict__
        obj = object()
        result = _serialize_value(obj)
        assert isinstance(result, str)
        assert "object" in result

    def test_serialize_exception_in_str(self):
        """Test handling of exceptions during string conversion."""

        class BadObject:
            def __str__(self):
                raise ValueError("Cannot convert to string")

        obj = BadObject()
        result = _serialize_value(obj)
        assert isinstance(result, str)
        assert "BadObject" in result

    def test_serialize_mixed_types_in_dict(self):
        """Test dict with mixed value types."""
        data = {
            "int": 42,
            "str": "hello",
            "bool": True,
            "none": None,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
        }
        result = _serialize_value(data)
        assert result["int"] == 42
        assert result["str"] == "hello"
        assert result["bool"] is True
        assert result["none"] is None
        assert result["list"] == [1, 2, 3]
        assert result["dict"]["nested"] == "value"

    def test_serialize_mixed_types_in_list(self):
        """Test list with mixed value types."""
        data = [42, "hello", True, None, [1, 2], {"key": "value"}]
        result = _serialize_value(data)
        assert result[0] == 42
        assert result[1] == "hello"
        assert result[2] is True
        assert result[3] is None
        assert result[4] == [1, 2]
        assert result[5]["key"] == "value"


class TestAuditLogDecorator:
    """Test suite for @audit_log decorator."""

    def test_decorator_basic_function(self, audit_engine):
        """Test decorator on basic function."""

        @audit_log(engine=audit_engine)
        def test_function():
            return "result"

        result = test_function()
        assert result == "result"
        assert audit_engine.get_stats()["events_logged"] == 1

    def test_decorator_preserves_function_name(self, audit_engine):
        """Test that decorator preserves function name."""

        @audit_log(engine=audit_engine)
        def my_function():
            pass

        assert my_function.__name__ == "my_function"

    def test_decorator_preserves_docstring(self, audit_engine):
        """Test that decorator preserves function docstring."""

        @audit_log(engine=audit_engine)
        def documented_function():
            """This is a docstring."""
            pass

        assert documented_function.__doc__ == "This is a docstring."

    def test_decorator_with_arguments(self, audit_engine):
        """Test decorator on function with arguments."""

        @audit_log(engine=audit_engine, capture_params=True)
        def add(a, b):
            return a + b

        result = add(2, 3)
        assert result == 5
        assert audit_engine.get_stats()["events_logged"] == 1

    def test_decorator_captures_parameters(self, audit_engine):
        """Test that decorator captures function parameters."""
        captured_params = []

        # Mock the log method to capture parameters
        original_log = audit_engine.log

        def mock_log(*args, **kwargs):
            captured_params.append(kwargs.get("parameters", {}))
            return original_log(*args, **kwargs)

        audit_engine.log = mock_log

        @audit_log(engine=audit_engine, capture_params=True)
        def test_function(x, y, z=10):
            return x + y + z

        test_function(1, 2, z=3)

        assert len(captured_params) == 1
        assert captured_params[0]["x"] == 1
        assert captured_params[0]["y"] == 2
        assert captured_params[0]["z"] == 3

    def test_decorator_captures_default_values(self, audit_engine):
        """Test that decorator captures default parameter values."""
        captured_params = []

        original_log = audit_engine.log

        def mock_log(*args, **kwargs):
            captured_params.append(kwargs.get("parameters", {}))
            return original_log(*args, **kwargs)

        audit_engine.log = mock_log

        @audit_log(engine=audit_engine, capture_params=True)
        def test_function(x, y=10, z=20):
            return x + y + z

        test_function(1)

        assert len(captured_params) == 1
        assert captured_params[0]["x"] == 1
        assert captured_params[0]["y"] == 10
        assert captured_params[0]["z"] == 20

    def test_decorator_excludes_self_parameter(self, audit_engine):
        """Test that 'self' parameter is excluded from capture."""
        captured_params = []

        original_log = audit_engine.log

        def mock_log(*args, **kwargs):
            captured_params.append(kwargs.get("parameters", {}))
            return original_log(*args, **kwargs)

        audit_engine.log = mock_log

        class TestClass:
            @audit_log(engine=audit_engine, capture_params=True)
            def method(self, x):
                return x

        obj = TestClass()
        obj.method(42)

        assert len(captured_params) == 1
        assert "self" not in captured_params[0]
        assert captured_params[0]["x"] == 42

    def test_decorator_excludes_cls_parameter(self, audit_engine):
        """Test that 'cls' parameter is excluded from capture."""
        captured_params = []

        original_log = audit_engine.log

        def mock_log(*args, **kwargs):
            captured_params.append(kwargs.get("parameters", {}))
            return original_log(*args, **kwargs)

        audit_engine.log = mock_log

        class TestClass:
            @classmethod
            @audit_log(engine=audit_engine, capture_params=True)
            def method(cls, x):
                return x

        TestClass.method(42)

        assert len(captured_params) == 1
        assert "cls" not in captured_params[0]
        assert captured_params[0]["x"] == 42

    def test_decorator_without_capture_params(self, audit_engine):
        """Test decorator with capture_params=False."""
        captured_params = []

        original_log = audit_engine.log

        def mock_log(*args, **kwargs):
            captured_params.append(kwargs.get("parameters", {}))
            return original_log(*args, **kwargs)

        audit_engine.log = mock_log

        @audit_log(engine=audit_engine, capture_params=False)
        def test_function(x, y):
            return x + y

        test_function(1, 2)

        assert len(captured_params) == 1
        assert captured_params[0] == {}

    def test_decorator_captures_result(self, audit_engine):
        """Test that decorator can capture return value."""
        captured_results = []

        original_log = audit_engine.log

        def mock_log(*args, **kwargs):
            captured_results.append(kwargs.get("result", {}))
            return original_log(*args, **kwargs)

        audit_engine.log = mock_log

        @audit_log(engine=audit_engine, capture_result=True)
        def test_function():
            return "test_result"

        test_function()

        assert len(captured_results) == 1
        assert captured_results[0]["data"] == "test_result"

    def test_decorator_without_capture_result(self, audit_engine):
        """Test decorator with capture_result=False."""
        captured_results = []

        original_log = audit_engine.log

        def mock_log(*args, **kwargs):
            captured_results.append(kwargs.get("result", {}))
            return original_log(*args, **kwargs)

        audit_engine.log = mock_log

        @audit_log(engine=audit_engine, capture_result=False)
        def test_function():
            return "test_result"

        test_function()

        assert len(captured_results) == 1
        assert "data" not in captured_results[0]

    def test_decorator_captures_exception(self, audit_engine):
        """Test that decorator captures exceptions."""
        captured_errors = []

        original_log = audit_engine.log

        def mock_log(*args, **kwargs):
            captured_errors.append(kwargs.get("error"))
            return original_log(*args, **kwargs)

        audit_engine.log = mock_log

        @audit_log(engine=audit_engine, capture_exceptions=True)
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_function()

        assert len(captured_errors) == 1
        assert captured_errors[0] is not None
        assert captured_errors[0]["occurred"] is True
        assert captured_errors[0]["type"] == "ValueError"
        assert "Test error" in captured_errors[0]["message"]
        assert captured_errors[0]["handled"] is False

    def test_decorator_re_raises_exception(self, audit_engine):
        """Test that decorator re-raises exceptions."""

        @audit_log(engine=audit_engine)
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError) as exc_info:
            failing_function()

        assert "Test error" in str(exc_info.value)

    def test_decorator_without_capture_exceptions(self, audit_engine):
        """Test decorator with capture_exceptions=False."""
        captured_errors = []

        original_log = audit_engine.log

        def mock_log(*args, **kwargs):
            captured_errors.append(kwargs.get("error"))
            return original_log(*args, **kwargs)

        audit_engine.log = mock_log

        @audit_log(engine=audit_engine, capture_exceptions=False)
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_function()

        assert len(captured_errors) == 1
        assert captured_errors[0] is None

    def test_decorator_records_performance(self, audit_engine):
        """Test that decorator records performance metrics."""
        captured_performance = []

        original_log = audit_engine.log

        def mock_log(*args, **kwargs):
            captured_performance.append(kwargs.get("performance", {}))
            return original_log(*args, **kwargs)

        audit_engine.log = mock_log

        @audit_log(engine=audit_engine)
        def slow_function():
            time.sleep(0.01)  # 10ms
            return "done"

        slow_function()

        assert len(captured_performance) == 1
        assert "duration_ms" in captured_performance[0]
        assert captured_performance[0]["duration_ms"] >= 10  # At least 10ms

    def test_decorator_with_category(self, audit_engine):
        """Test decorator with custom category."""

        @audit_log(engine=audit_engine, category="DATABASE")
        def database_function():
            return "data"

        database_function()
        # Should not raise an error
        assert audit_engine.get_stats()["events_logged"] == 1

    def test_decorator_with_action_type(self, audit_engine):
        """Test decorator with custom action type."""

        @audit_log(engine=audit_engine, action_type="READ")
        def read_function():
            return "data"

        read_function()
        assert audit_engine.get_stats()["events_logged"] == 1

    def test_decorator_with_extra_fields(self, audit_engine):
        """Test decorator with extra custom fields."""

        @audit_log(
            engine=audit_engine,
            resource_type="table",
            metadata={"custom": "value"},
        )
        def test_function():
            return "result"

        test_function()
        assert audit_engine.get_stats()["events_logged"] == 1

    def test_decorator_disabled_engine(self):
        """Test decorator with disabled audit engine."""
        config = AuditConfig(config_dict={"vigil": {"core": {"enabled": False}}})
        engine = AuditEngine(config=config)

        @audit_log(engine=engine)
        def test_function():
            return "result"

        result = test_function()
        assert result == "result"
        assert engine.get_stats()["events_logged"] == 0

    def test_decorator_logging_failure_doesnt_break_function(self, audit_engine):
        """Test that logging failure doesn't prevent function execution."""

        # Mock the log method to raise an exception
        def failing_log(*args, **kwargs):
            raise Exception("Logging failed")

        audit_engine.log = failing_log

        @audit_log(engine=audit_engine)
        def test_function():
            return "result"

        # Function should still execute and return result
        result = test_function()
        assert result == "result"

    def test_decorator_parameter_capture_error(self, audit_engine):
        """Test handling of errors during parameter capture."""
        captured_params = []

        original_log = audit_engine.log

        def mock_log(*args, **kwargs):
            captured_params.append(kwargs.get("parameters", {}))
            return original_log(*args, **kwargs)

        audit_engine.log = mock_log

        # Function with *args and **kwargs that might cause issues
        @audit_log(engine=audit_engine, capture_params=True)
        def complex_function(*args, **kwargs):
            return "result"

        complex_function(1, 2, 3, x=4, y=5)

        # Should have captured parameters or error message
        assert len(captured_params) == 1

    def test_decorator_with_varargs(self, audit_engine):
        """Test decorator on function with *args."""
        captured_params = []

        original_log = audit_engine.log

        def mock_log(*args, **kwargs):
            captured_params.append(kwargs.get("parameters", {}))
            return original_log(*args, **kwargs)

        audit_engine.log = mock_log

        @audit_log(engine=audit_engine, capture_params=True)
        def varargs_function(*args):
            return sum(args)

        result = varargs_function(1, 2, 3, 4)
        assert result == 10
        assert len(captured_params) == 1

    def test_decorator_with_kwargs(self, audit_engine):
        """Test decorator on function with **kwargs."""
        captured_params = []

        original_log = audit_engine.log

        def mock_log(*args, **kwargs):
            captured_params.append(kwargs.get("parameters", {}))
            return original_log(*args, **kwargs)

        audit_engine.log = mock_log

        @audit_log(engine=audit_engine, capture_params=True)
        def kwargs_function(**kwargs):
            return kwargs

        result = kwargs_function(a=1, b=2, c=3)
        assert result == {"a": 1, "b": 2, "c": 3}
        assert len(captured_params) == 1

    def test_decorator_records_success_status(self, audit_engine):
        """Test that successful execution records SUCCESS status."""
        captured_results = []

        original_log = audit_engine.log

        def mock_log(*args, **kwargs):
            captured_results.append(kwargs.get("result", {}))
            return original_log(*args, **kwargs)

        audit_engine.log = mock_log

        @audit_log(engine=audit_engine)
        def test_function():
            return "success"

        test_function()

        assert len(captured_results) == 1
        assert captured_results[0]["status"] == "SUCCESS"

    def test_decorator_records_failure_status(self, audit_engine):
        """Test that failed execution records FAILURE status."""
        captured_results = []

        original_log = audit_engine.log

        def mock_log(*args, **kwargs):
            captured_results.append(kwargs.get("result", {}))
            return original_log(*args, **kwargs)

        audit_engine.log = mock_log

        @audit_log(engine=audit_engine)
        def failing_function():
            raise ValueError("Error")

        with pytest.raises(ValueError):
            failing_function()

        assert len(captured_results) == 1
        assert captured_results[0]["status"] == "FAILURE"


class TestDecoratorEdgeCases:
    """Test edge cases for decorator functionality."""

    def test_decorator_on_generator_function(self, audit_engine):
        """Test decorator on generator function."""

        @audit_log(engine=audit_engine)
        def generator_function():
            yield 1
            yield 2
            yield 3

        gen = generator_function()
        assert list(gen) == [1, 2, 3]
        assert audit_engine.get_stats()["events_logged"] == 1

    def test_decorator_on_async_function_returns_coroutine(self, audit_engine):
        """Test that decorator works with async functions."""

        @audit_log(engine=audit_engine)
        async def async_function():
            return "async_result"

        # The function should return a coroutine
        import inspect

        result = async_function()
        assert inspect.iscoroutine(result)
        result.close()  # Clean up the coroutine

    def test_decorator_with_none_return_value(self, audit_engine):
        """Test decorator on function returning None."""

        @audit_log(engine=audit_engine, capture_result=True)
        def returns_none():
            return None

        result = returns_none()
        assert result is None
        assert audit_engine.get_stats()["events_logged"] == 1

    def test_decorator_with_complex_return_value(self, audit_engine):
        """Test decorator with complex return values."""

        @audit_log(engine=audit_engine, capture_result=True)
        def complex_return():
            return {
                "data": [1, 2, 3],
                "metadata": {"count": 3},
                "nested": {"deep": {"value": 42}},
            }

        result = complex_return()
        assert result["data"] == [1, 2, 3]
        assert audit_engine.get_stats()["events_logged"] == 1

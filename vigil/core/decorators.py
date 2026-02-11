"""Decorators for automatic audit logging."""

import functools
import inspect
import time
import traceback
from typing import Any, Callable, Optional

from vigil.core.engine import AuditEngine


def audit_log(
    category: str = "SYSTEM",
    action_type: str = "EXECUTE",
    resource_type: Optional[str] = None,
    capture_params: bool = True,
    capture_result: bool = False,
    capture_exceptions: bool = True,
    engine: Optional[AuditEngine] = None,
    **extra_fields,
):
    """
    Decorator for automatic audit logging of function calls.

    Args:
        category: Action category (DATABASE, API, FILE, etc.)
        action_type: Action type (READ, WRITE, EXECUTE, etc.)
        resource_type: Resource type (table, file, endpoint, function)
        capture_params: Whether to capture function parameters
        capture_result: Whether to capture function return value
        capture_exceptions: Whether to capture exceptions
        engine: AuditEngine instance (uses default if None)
        **extra_fields: Additional event fields

    Example:
        @audit_log
        def my_function():
            pass

        @audit_log(category="DATABASE", action_type="QUERY")
        def execute_query(sql, params):
            return db.execute(sql, params)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get engine
            if engine:
                audit_engine = engine
            else:
                from vigil import get_default_engine

                audit_engine = get_default_engine()

            # Skip if disabled
            if not audit_engine.config.enabled:
                return func(*args, **kwargs)

            # Start timing
            start_time = time.time()

            # Capture function info
            action_name = func.__name__
            module_name = func.__module__

            # Capture parameters
            parameters = {}
            if capture_params:
                try:
                    # Get function signature
                    sig = inspect.signature(func)
                    bound_args = sig.bind(*args, **kwargs)
                    bound_args.apply_defaults()

                    # Convert to dict, excluding 'self' and 'cls'
                    parameters = {
                        k: _serialize_value(v)
                        for k, v in bound_args.arguments.items()
                        if k not in ("self", "cls")
                    }
                except Exception as e:
                    parameters = {"_capture_error": str(e)}

            # Execute function
            result = None
            status = "SUCCESS"
            error_info = None

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = "FAILURE"

                if capture_exceptions:
                    error_info = {
                        "occurred": True,
                        "type": type(e).__name__,
                        "message": str(e),
                        "stack_trace": traceback.format_exc(),
                        "handled": False,
                    }

                raise  # Re-raise the exception
            finally:
                # Calculate duration
                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000

                # Capture result
                result_data = {}
                if capture_result and result is not None:
                    result_data["data"] = _serialize_value(result)

                # Build custom fields
                custom = {
                    "function": action_name,
                    "module": module_name,
                }

                # Log event
                try:
                    audit_engine.log(
                        action=action_name,
                        category=category,
                        action_type=action_type,
                        parameters=parameters,
                        result={"status": status, **result_data},
                        performance={"duration_ms": duration_ms},
                        error=error_info,
                        custom=custom,
                        **extra_fields,
                    )
                except Exception as log_error:
                    # Don't fail the original function if logging fails
                    import logging

                    logging.getLogger(__name__).error(f"Failed to log audit event: {log_error}")

        return wrapper

    return decorator


def _serialize_value(value: Any, max_length: int = 1000, max_depth: int = 5, depth: int = 0) -> Any:
    """
    Serialize value for logging with depth limiting to prevent stack overflow.

    Args:
        value: Value to serialize
        max_length: Maximum string length
        max_depth: Maximum recursion depth (default: 5)
        depth: Current recursion depth (internal use)

    Returns:
        Serialized value
    """
    # Check depth limit to prevent stack overflow
    if depth > max_depth:
        return f"<max depth {max_depth} exceeded>"

    # Handle None
    if value is None:
        return None

    # Handle primitives
    if isinstance(value, (bool, int, float, str)):
        if isinstance(value, str) and len(value) > max_length:
            return value[:max_length] + "... (truncated)"
        return value

    # Handle collections (limit size and depth)
    if isinstance(value, (list, tuple)):
        if len(value) > 10:
            return f"<{type(value).__name__} with {len(value)} items>"
        return [_serialize_value(item, max_length, max_depth, depth + 1) for item in value[:10]]

    if isinstance(value, dict):
        if len(value) > 20:
            return f"<dict with {len(value)} keys>"
        return {
            k: _serialize_value(v, max_length, max_depth, depth + 1)
            for k, v in list(value.items())[:20]
        }

    # Handle objects with __dict__
    if hasattr(value, "__dict__"):
        return f"<{type(value).__name__} object>"

    # Fallback to string representation
    try:
        str_value = str(value)
        if len(str_value) > max_length:
            return str_value[:max_length] + "... (truncated)"
        return str_value
    except Exception:
        return f"<{type(value).__name__}>"

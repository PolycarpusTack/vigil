"""Enumerations for Vigil."""

from enum import Enum


class ActionCategory(str, Enum):
    """Valid action categories for audit events."""

    DATABASE = "DATABASE"
    API = "API"
    AUTH = "AUTH"
    FILE = "FILE"
    SYSTEM = "SYSTEM"
    NETWORK = "NETWORK"
    SECURITY = "SECURITY"
    COMPLIANCE = "COMPLIANCE"
    USER = "USER"
    ADMIN = "ADMIN"


class ActionType(str, Enum):
    """Valid action types for audit events."""

    READ = "READ"
    WRITE = "WRITE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    EXECUTE = "EXECUTE"
    CREATE = "CREATE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    ACCESS = "ACCESS"
    MODIFY = "MODIFY"
    GRANT = "GRANT"
    REVOKE = "REVOKE"
    APPROVE = "APPROVE"
    REJECT = "REJECT"


def validate_category(category: str) -> str:
    """Validate and normalize action category.

    Args:
        category: Category string to validate

    Returns:
        Validated category string (uppercase)

    Raises:
        ValueError: If category is invalid
    """
    if not category:
        raise ValueError("category cannot be empty")

    category_upper = category.upper()

    try:
        ActionCategory(category_upper)
        return category_upper
    except ValueError:
        valid_categories = ", ".join([c.value for c in ActionCategory])
        raise ValueError(f"Invalid category '{category}'. " f"Valid categories: {valid_categories}")


def validate_action_type(action_type: str) -> str:
    """Validate and normalize action type.

    Args:
        action_type: Action type string to validate

    Returns:
        Validated action type string (uppercase)

    Raises:
        ValueError: If action type is invalid
    """
    if not action_type:
        raise ValueError("action_type cannot be empty")

    action_type_upper = action_type.upper()

    try:
        ActionType(action_type_upper)
        return action_type_upper
    except ValueError:
        valid_types = ", ".join([t.value for t in ActionType])
        raise ValueError(f"Invalid action_type '{action_type}'. " f"Valid types: {valid_types}")

"""Unit tests for Vigil enumerations.

Tests cover:
- Category validation and normalization
- Action type validation and normalization
- Error messages for invalid values
- Case insensitivity handling
- Empty/None value handling
"""

import pytest

from vigil.core.enums import (
    ActionCategory,
    ActionType,
    validate_action_type,
    validate_category,
)


class TestActionCategory:
    """Test suite for ActionCategory enum."""

    def test_all_category_values_are_valid(self):
        """Test that all category enum values can be accessed."""
        categories = [
            ActionCategory.DATABASE,
            ActionCategory.API,
            ActionCategory.AUTH,
            ActionCategory.FILE,
            ActionCategory.SYSTEM,
            ActionCategory.NETWORK,
            ActionCategory.SECURITY,
            ActionCategory.COMPLIANCE,
            ActionCategory.USER,
            ActionCategory.ADMIN,
        ]
        assert len(categories) == 10
        assert all(isinstance(cat, ActionCategory) for cat in categories)

    def test_category_string_values(self):
        """Test that category enum values match expected strings."""
        assert ActionCategory.DATABASE.value == "DATABASE"
        assert ActionCategory.API.value == "API"
        assert ActionCategory.AUTH.value == "AUTH"
        assert ActionCategory.FILE.value == "FILE"
        assert ActionCategory.SYSTEM.value == "SYSTEM"

    def test_category_enum_comparison(self):
        """Test that category enum values can be compared."""
        assert ActionCategory.DATABASE == ActionCategory.DATABASE
        assert ActionCategory.DATABASE != ActionCategory.API
        assert ActionCategory.DATABASE.value == "DATABASE"


class TestActionType:
    """Test suite for ActionType enum."""

    def test_all_action_type_values_are_valid(self):
        """Test that all action type enum values can be accessed."""
        action_types = [
            ActionType.READ,
            ActionType.WRITE,
            ActionType.UPDATE,
            ActionType.DELETE,
            ActionType.EXECUTE,
            ActionType.CREATE,
            ActionType.LOGIN,
            ActionType.LOGOUT,
            ActionType.ACCESS,
            ActionType.MODIFY,
            ActionType.GRANT,
            ActionType.REVOKE,
            ActionType.APPROVE,
            ActionType.REJECT,
        ]
        assert len(action_types) == 14
        assert all(isinstance(at, ActionType) for at in action_types)

    def test_action_type_string_values(self):
        """Test that action type enum values match expected strings."""
        assert ActionType.READ.value == "READ"
        assert ActionType.WRITE.value == "WRITE"
        assert ActionType.UPDATE.value == "UPDATE"
        assert ActionType.DELETE.value == "DELETE"
        assert ActionType.EXECUTE.value == "EXECUTE"

    def test_action_type_enum_comparison(self):
        """Test that action type enum values can be compared."""
        assert ActionType.READ == ActionType.READ
        assert ActionType.READ != ActionType.WRITE
        assert ActionType.READ.value == "READ"


class TestValidateCategory:
    """Test suite for validate_category function."""

    @pytest.mark.parametrize(
        "input_category,expected_output",
        [
            ("DATABASE", "DATABASE"),
            ("database", "DATABASE"),
            ("Database", "DATABASE"),
            ("DaTaBaSe", "DATABASE"),
            ("API", "API"),
            ("api", "API"),
            ("AUTH", "AUTH"),
            ("auth", "AUTH"),
            ("FILE", "FILE"),
            ("file", "FILE"),
            ("SYSTEM", "SYSTEM"),
            ("system", "SYSTEM"),
            ("NETWORK", "NETWORK"),
            ("network", "NETWORK"),
            ("SECURITY", "SECURITY"),
            ("security", "SECURITY"),
            ("COMPLIANCE", "COMPLIANCE"),
            ("compliance", "COMPLIANCE"),
            ("USER", "USER"),
            ("user", "USER"),
            ("ADMIN", "ADMIN"),
            ("admin", "ADMIN"),
        ],
    )
    def test_validate_category_success(self, input_category, expected_output):
        """Test successful category validation with various cases."""
        result = validate_category(input_category)
        assert result == expected_output
        assert isinstance(result, str)

    @pytest.mark.parametrize(
        "invalid_category",
        [
            "INVALID",
            "invalid",
            "Unknown",
            "DB",
            "SYS",
            "random_category",
            "123",
            "DATA BASE",  # Space in middle
            "DATABASE ",  # Trailing space (will be uppercase but still invalid enum)
        ],
    )
    def test_validate_category_invalid_value(self, invalid_category):
        """Test that invalid category values raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_category(invalid_category)

        error_msg = str(exc_info.value)
        assert "Invalid category" in error_msg
        assert invalid_category.upper() in error_msg or invalid_category in error_msg
        assert "Valid categories:" in error_msg

    def test_validate_category_empty_string(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_category("")

        assert "category cannot be empty" in str(exc_info.value)

    def test_validate_category_none(self):
        """Test that None value raises appropriate error."""
        with pytest.raises((ValueError, AttributeError)):
            validate_category(None)

    def test_validate_category_whitespace_only(self):
        """Test that whitespace-only string is treated as invalid."""
        # Whitespace will be uppercased and fail enum validation
        with pytest.raises(ValueError) as exc_info:
            validate_category("   ")

        error_msg = str(exc_info.value)
        assert "Invalid category" in error_msg

    def test_validate_category_error_message_includes_valid_options(self):
        """Test that error message includes all valid categories."""
        with pytest.raises(ValueError) as exc_info:
            validate_category("INVALID_CATEGORY")

        error_msg = str(exc_info.value)
        assert "DATABASE" in error_msg
        assert "API" in error_msg
        assert "AUTH" in error_msg
        assert "SYSTEM" in error_msg


class TestValidateActionType:
    """Test suite for validate_action_type function."""

    @pytest.mark.parametrize(
        "input_type,expected_output",
        [
            ("READ", "READ"),
            ("read", "READ"),
            ("Read", "READ"),
            ("ReAd", "READ"),
            ("WRITE", "WRITE"),
            ("write", "WRITE"),
            ("UPDATE", "UPDATE"),
            ("update", "UPDATE"),
            ("DELETE", "DELETE"),
            ("delete", "DELETE"),
            ("EXECUTE", "EXECUTE"),
            ("execute", "EXECUTE"),
            ("CREATE", "CREATE"),
            ("create", "CREATE"),
            ("LOGIN", "LOGIN"),
            ("login", "LOGIN"),
            ("LOGOUT", "LOGOUT"),
            ("logout", "LOGOUT"),
            ("ACCESS", "ACCESS"),
            ("access", "ACCESS"),
            ("MODIFY", "MODIFY"),
            ("modify", "MODIFY"),
            ("GRANT", "GRANT"),
            ("grant", "GRANT"),
            ("REVOKE", "REVOKE"),
            ("revoke", "REVOKE"),
            ("APPROVE", "APPROVE"),
            ("approve", "APPROVE"),
            ("REJECT", "REJECT"),
            ("reject", "REJECT"),
        ],
    )
    def test_validate_action_type_success(self, input_type, expected_output):
        """Test successful action type validation with various cases."""
        result = validate_action_type(input_type)
        assert result == expected_output
        assert isinstance(result, str)

    @pytest.mark.parametrize(
        "invalid_type",
        [
            "INVALID",
            "invalid",
            "Unknown",
            "RUN",
            "EXEC",
            "random_type",
            "123",
            "READ WRITE",  # Space in middle
        ],
    )
    def test_validate_action_type_invalid_value(self, invalid_type):
        """Test that invalid action type values raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_action_type(invalid_type)

        error_msg = str(exc_info.value)
        assert "Invalid action_type" in error_msg
        assert invalid_type.upper() in error_msg or invalid_type in error_msg
        assert "Valid types:" in error_msg

    def test_validate_action_type_empty_string(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_action_type("")

        assert "action_type cannot be empty" in str(exc_info.value)

    def test_validate_action_type_none(self):
        """Test that None value raises appropriate error."""
        with pytest.raises((ValueError, AttributeError)):
            validate_action_type(None)

    def test_validate_action_type_whitespace_only(self):
        """Test that whitespace-only string is treated as invalid."""
        with pytest.raises(ValueError) as exc_info:
            validate_action_type("   ")

        error_msg = str(exc_info.value)
        assert "Invalid action_type" in error_msg

    def test_validate_action_type_error_message_includes_valid_options(self):
        """Test that error message includes all valid action types."""
        with pytest.raises(ValueError) as exc_info:
            validate_action_type("INVALID_TYPE")

        error_msg = str(exc_info.value)
        assert "READ" in error_msg
        assert "WRITE" in error_msg
        assert "EXECUTE" in error_msg
        assert "DELETE" in error_msg


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_numeric_string_category(self):
        """Test that numeric strings are rejected."""
        with pytest.raises(ValueError):
            validate_category("12345")

    def test_numeric_string_action_type(self):
        """Test that numeric strings are rejected."""
        with pytest.raises(ValueError):
            validate_action_type("12345")

    def test_special_characters_category(self):
        """Test that categories with special characters are rejected."""
        with pytest.raises(ValueError):
            validate_category("DATA@BASE")

    def test_special_characters_action_type(self):
        """Test that action types with special characters are rejected."""
        with pytest.raises(ValueError):
            validate_action_type("READ#WRITE")

    def test_unicode_category(self):
        """Test that unicode categories are rejected."""
        with pytest.raises(ValueError):
            validate_category("DATAB🔐SE")

    def test_unicode_action_type(self):
        """Test that unicode action types are rejected."""
        with pytest.raises(ValueError):
            validate_action_type("RE🔒AD")

    def test_very_long_category(self):
        """Test that very long category strings are rejected."""
        long_category = "A" * 1000
        with pytest.raises(ValueError):
            validate_category(long_category)

    def test_very_long_action_type(self):
        """Test that very long action type strings are rejected."""
        long_type = "A" * 1000
        with pytest.raises(ValueError):
            validate_action_type(long_type)


class TestTypeConsistency:
    """Test type consistency and return types."""

    def test_validate_category_returns_string(self):
        """Test that validate_category always returns a string."""
        result = validate_category("database")
        assert isinstance(result, str)
        assert result == "DATABASE"

    def test_validate_action_type_returns_string(self):
        """Test that validate_action_type always returns a string."""
        result = validate_action_type("read")
        assert isinstance(result, str)
        assert result == "READ"

    def test_uppercase_normalization_category(self):
        """Test that all valid inputs are normalized to uppercase."""
        inputs = ["database", "Database", "DATABASE", "DaTaBaSe"]
        results = [validate_category(inp) for inp in inputs]
        assert all(r == "DATABASE" for r in results)

    def test_uppercase_normalization_action_type(self):
        """Test that all valid inputs are normalized to uppercase."""
        inputs = ["read", "Read", "READ", "ReAd"]
        results = [validate_action_type(inp) for inp in inputs]
        assert all(r == "READ" for r in results)

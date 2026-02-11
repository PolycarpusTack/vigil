#!/usr/bin/env python3
"""Basic example of using the Vigil."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from vigil import AuditContext, AuditEngine, audit_log


def main():
    """Run basic examples."""
    print("=" * 80)
    print("Vigil - Basic Example")
    print("=" * 80)

    # Example 1: Initialize engine
    print("\n[1] Initializing audit engine...")
    audit = AuditEngine()
    print(f"✓ Engine initialized: {audit}")

    # Example 2: Direct logging
    print("\n[2] Direct API logging...")
    audit.log(
        action="user_login",
        category="AUTH",
        action_type="LOGIN",
        actor={"username": "john.doe", "ip_address": "192.168.1.100"},
        result={"status": "SUCCESS"},
        performance={"duration_ms": 150},
    )
    print("✓ Event logged via direct API")

    # Example 3: Decorator-based logging
    print("\n[3] Decorator-based logging...")

    @audit_log(category="DATABASE", action_type="QUERY")
    def execute_query(sql, params=None):
        """Execute a database query."""
        # Simulate query execution
        import time

        time.sleep(0.05)  # Simulate 50ms query
        return [{"id": 1, "name": "John"}, {"id": 2, "name": "Jane"}]

    result = execute_query("SELECT * FROM users WHERE id = :1", params=[1])
    print(f"✓ Query executed: {len(result)} rows")

    # Example 4: Context manager
    print("\n[4] Context manager logging...")
    with AuditContext(action="FILE_EXPORT", category="FILE", action_type="WRITE"):
        # Simulate file export
        import time

        time.sleep(0.1)
        print("✓ File exported")

    # Example 5: Exception handling
    print("\n[5] Exception handling...")

    @audit_log(category="API", action_type="EXECUTE", capture_exceptions=True)
    def failing_function():
        """Function that raises an exception."""
        raise ValueError("This is a test error")

    try:
        failing_function()
    except ValueError:
        print("✓ Exception captured in audit log")

    # Example 6: PII sanitization
    print("\n[6] PII sanitization...")
    audit.log(
        action="user_registration",
        category="AUTH",
        action_type="CREATE",
        actor={"username": "jane.smith", "email": "jane.smith@example.com"},
        parameters={
            "email": "jane.smith@example.com",
            "password": "supersecret123",
            "credit_card": "4532-1234-5678-9010",
            "ssn": "123-45-6789",
        },
    )
    print("✓ Sensitive data sanitized (check log file)")

    # Example 7: Performance metrics
    print("\n[7] Performance tracking...")

    @audit_log(category="COMPUTATION", action_type="EXECUTE")
    def heavy_computation(n):
        """Simulate heavy computation."""
        import time

        time.sleep(0.2)
        return sum(range(n))

    result = heavy_computation(1000000)
    print(f"✓ Computation completed: result={result}")

    # Display statistics
    print("\n[8] Engine statistics:")
    stats = audit.get_stats()
    for key, value in stats.items():
        print(f"  - {key}: {value}")

    # Show where logs are stored
    print(f"\n[9] Logs stored in: ./logs/audit/")
    print("  View with: cat logs/audit/*.log | head -20")

    print("\n" + "=" * 80)
    print("Example completed successfully! Check ./logs/audit/ for logs.")
    print("=" * 80)


if __name__ == "__main__":
    main()

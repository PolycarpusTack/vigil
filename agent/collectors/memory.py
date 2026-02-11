"""Memory metric collector."""

import psutil


def collect_memory() -> dict:
    """Return memory usage metrics."""
    mem = psutil.virtual_memory()
    return {
        "memory_percent": mem.percent,
        "memory_used_mb": round(mem.used / (1024 * 1024), 2),
        "memory_total_mb": round(mem.total / (1024 * 1024), 2),
    }

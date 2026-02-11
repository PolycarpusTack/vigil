"""CPU metric collector."""

import psutil


def collect_cpu() -> float:
    """Return current CPU usage percentage."""
    return psutil.cpu_percent(interval=1)

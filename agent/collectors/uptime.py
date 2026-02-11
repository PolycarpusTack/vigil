"""Uptime metric collector."""

import time

import psutil


def collect_uptime() -> float:
    """Return system uptime in seconds."""
    return round(time.time() - psutil.boot_time(), 2)

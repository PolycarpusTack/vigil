"""Disk metric collector."""

import os
import platform

import psutil


def _default_disk_path() -> str:
    """Return the platform-appropriate default root path."""
    if platform.system() == "Windows":
        return os.environ.get("SystemDrive", "C:\\") + "\\"
    return "/"


def collect_disk(path: str = "") -> dict:
    """Return disk usage metrics for the given mount point.

    Args:
        path: Filesystem path to check. Defaults to platform root if empty.

    Returns:
        Dict with disk_percent, disk_used_gb, disk_total_gb.

    Raises:
        FileNotFoundError: If the path does not exist.
        OSError: If disk usage cannot be read.
    """
    if not path:
        path = _default_disk_path()

    if not os.path.exists(path):
        raise FileNotFoundError(f"Disk path does not exist: {path}")

    usage = psutil.disk_usage(path)
    return {
        "disk_percent": usage.percent,
        "disk_used_gb": round(usage.used / (1024**3), 2),
        "disk_total_gb": round(usage.total / (1024**3), 2),
    }

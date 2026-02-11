"""Network metric collector."""

import psutil


def collect_network() -> dict:
    """Return network I/O counters."""
    net = psutil.net_io_counters()
    return {
        "network_bytes_sent": net.bytes_sent,
        "network_bytes_recv": net.bytes_recv,
    }

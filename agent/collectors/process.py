"""Process metric collector."""

import psutil


def collect_top_processes(count: int = 5) -> dict:
    """Return top N processes by CPU usage and total process count."""
    procs = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            info = proc.info
            procs.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    process_count = len(procs)

    # Sort by CPU percent descending
    procs.sort(key=lambda p: p.get("cpu_percent") or 0, reverse=True)
    top = procs[:count]

    top_processes = []
    for p in top:
        entry = {
            "pid": p["pid"],
            "name": p["name"] or "unknown",
            "cpu_percent": p.get("cpu_percent") or 0,
            "memory_percent": p.get("memory_percent") or 0,
        }
        top_processes.append(entry)

    return {
        "process_count": process_count,
        "top_processes": top_processes,
    }

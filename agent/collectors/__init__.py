"""System metric collectors."""

from agent.collectors.cpu import collect_cpu
from agent.collectors.disk import collect_disk
from agent.collectors.memory import collect_memory
from agent.collectors.network import collect_network
from agent.collectors.process import collect_top_processes
from agent.collectors.uptime import collect_uptime

__all__ = [
    "collect_cpu",
    "collect_memory",
    "collect_disk",
    "collect_network",
    "collect_top_processes",
    "collect_uptime",
]

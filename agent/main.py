"""Server monitoring agent main loop."""

import logging
import platform
import signal
import sys
import time
from datetime import datetime, timezone

from agent.collectors.cpu import collect_cpu
from agent.collectors.disk import collect_disk
from agent.collectors.memory import collect_memory
from agent.collectors.network import collect_network
from agent.collectors.process import collect_top_processes
from agent.collectors.uptime import collect_uptime
from agent.config import AgentConfig
from agent.health import HealthTracker
from agent.transport.http_sender import HTTPSender

logger = logging.getLogger(__name__)

_running = True


def _handle_signal(signum, frame):
    """Handle shutdown signals."""
    global _running
    logger.info(f"Received signal {signum}, shutting down...")
    _running = False


def collect_all_metrics(config: AgentConfig) -> dict:
    """Collect all system metrics into a single payload."""
    cpu = collect_cpu()
    mem = collect_memory()
    disk = collect_disk()
    net = collect_network()
    procs = collect_top_processes(count=config.top_processes_count)
    uptime = collect_uptime()

    return {
        "agent_id": config.agent_id,
        "hostname": platform.node(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": {
            "cpu_percent": cpu,
            **mem,
            **disk,
            **net,
            "uptime_seconds": uptime,
            **procs,
        },
    }


def run(config: AgentConfig):
    """Run the agent main loop."""
    global _running  # noqa: F824 — assigned in _handle_signal

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    sender = HTTPSender(
        collector_url=config.collector_url,
        api_key=config.api_key,
    )
    health = HealthTracker(agent_id=config.agent_id)

    logger.info(
        f"Agent '{config.agent_id}' starting. "
        f"Collector: {config.collector_url}, Interval: {config.interval_seconds}s"
    )

    while _running:
        try:
            payload = collect_all_metrics(config)
            success = sender.send_metrics(payload)
            if success:
                health.record_success()
                logger.info(f"Metrics sent successfully for {config.agent_id}")
            else:
                health.record_failure()
                logger.warning("Failed to send metrics, will retry next interval")
        except Exception as e:
            health.record_failure()
            logger.error(f"Error in collection cycle: {e}", exc_info=True)

        # Sleep in small increments to respond to signals promptly
        for _ in range(config.interval_seconds):
            if not _running:
                break
            time.sleep(1)

    sender.close()
    logger.info("Agent stopped")


def main():
    """Entry point for the monitoring agent."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    # Load config from YAML if provided, otherwise use env/defaults
    if len(sys.argv) > 1:
        config = AgentConfig.from_yaml(sys.argv[1])
    else:
        config = AgentConfig()

    run(config)


if __name__ == "__main__":
    main()

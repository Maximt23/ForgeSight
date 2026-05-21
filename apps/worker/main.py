"""
Worker entrypoint.

Run with:
    python -m apps.worker.main

Or via Arq's CLI (recommended in production):
    arq apps.worker.main.WorkerSettings

Copyright (c) 2024-2026 Walmart Inc. All rights reserved.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


# ─── Job functions ─────────────────────────────────────────────────────


async def parse_dxf_job(ctx: dict, file_path: str, store_number: str) -> dict[str, Any]:
    """Parse a DXF file in the background."""
    logger.info("worker.parse_dxf.start", extra={"file_path": file_path, "store_number": store_number})
    # TODO: wire to packages.import.dxf parser when extracted
    return {
        "file_path": file_path,
        "store_number": store_number,
        "device_count": 0,
        "status": "stub_not_implemented",
    }


async def sync_camera_health_job(ctx: dict, store_number: str) -> dict[str, Any]:
    """Pull fresh camera health from Saone for a store."""
    from packages.integrations.saone import SaoneClient

    async with SaoneClient() as client:
        summary = await client.get_store_summary(store_number)

    logger.info("worker.sync_camera_health.done", extra={"store_number": store_number, "cameras": summary.get("total_cameras")})
    return summary


async def sync_network_health_job(ctx: dict, store_number: str) -> dict[str, Any]:
    """Pull fresh switch telemetry from Grafana for a store."""
    from packages.integrations.grafana import GrafanaClient

    async with GrafanaClient() as client:
        switches = await client.get_switches(store_number)

    logger.info("worker.sync_network_health.done", extra={"store_number": store_number, "switches": len(switches)})
    return {
        "store_number": store_number,
        "switch_count": len(switches),
        "online": sum(1 for s in switches if s.is_online),
    }


async def build_store_dashboard_job(ctx: dict, store_number: str, devices: list[dict]) -> dict[str, Any]:
    """Build the full master-bridge view for a store."""
    from packages.integrations.master import MasterBridge

    async with MasterBridge() as bridge:
        view = await bridge.build_store_view(store_number, devices)

    logger.info("worker.build_store_dashboard.done", extra={"store_number": store_number})
    return view


# ─── Worker settings ───────────────────────────────────────────────────


class WorkerSettings:
    """Arq worker configuration."""

    functions = [
        parse_dxf_job,
        sync_camera_health_job,
        sync_network_health_job,
        build_store_dashboard_job,
    ]

    # Redis connection
    from arq.connections import RedisSettings

    redis_settings = RedisSettings.from_dsn(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

    # Concurrency
    max_jobs = int(os.getenv("WORKER_MAX_JOBS", "10"))
    job_timeout = int(os.getenv("WORKER_JOB_TIMEOUT_SECONDS", "300"))

    # Periodic cron jobs (every 5 min, sync all known stores)
    # cron_jobs = [
    #     cron(sync_camera_health_job, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}),
    # ]


# ─── Direct entrypoint (`python -m apps.worker.main`) ─────────────────


def main() -> None:
    """Entrypoint for `python -m apps.worker.main`."""
    import logging

    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger.info("worker.starting", extra={
        "redis_url": os.getenv("REDIS_URL"),
        "max_jobs": WorkerSettings.max_jobs,
    })

    from arq.worker import run_worker

    run_worker(WorkerSettings)


if __name__ == "__main__":
    main()

from __future__ import annotations

import asyncio
import logging

from app.db.session import AsyncSessionLocal
from app.jobs.scheduler import build_scheduler
from app.services.monitoring import MonitoringService

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    async with AsyncSessionLocal() as session:
        service = MonitoringService(session)
        await service.ensure_default_notification_channel()

    scheduler = build_scheduler()
    scheduler.start()
    logging.info("Scheduler started")

    stop_event = asyncio.Event()
    try:
        await stop_event.wait()
    finally:
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())

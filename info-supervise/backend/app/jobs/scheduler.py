from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.services.monitoring import MonitoringService


def build_scheduler() -> AsyncIOScheduler:
    settings = get_settings()
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(run_app_checks_job, "interval", minutes=settings.app_monitor_interval_minutes, id="monitor_apps")
    scheduler.add_job(
        run_publisher_discovery_job,
        "interval",
        hours=settings.publisher_monitor_interval_hours,
        id="discover_publishers",
    )
    scheduler.add_job(
        run_notification_dispatch_job,
        "interval",
        minutes=settings.notification_interval_minutes,
        id="deliver_notifications",
    )
    if settings.digest_enabled:
        scheduler.add_job(
            run_digest_job,
            "cron",
            hour=settings.digest_hour,
            minute=0,
            id="generate_digest",
        )
    return scheduler


async def run_app_checks_job() -> None:
    async with AsyncSessionLocal() as session:
        service = MonitoringService(session)
        await service.run_app_checks()


async def run_publisher_discovery_job() -> None:
    async with AsyncSessionLocal() as session:
        service = MonitoringService(session)
        await service.run_publisher_discovery()


async def run_notification_dispatch_job() -> None:
    async with AsyncSessionLocal() as session:
        service = MonitoringService(session)
        await service.dispatch_pending_events()


async def run_digest_job() -> None:
    async with AsyncSessionLocal() as session:
        service = MonitoringService(session)
        await service.generate_digest()

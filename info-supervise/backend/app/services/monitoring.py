from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from time import perf_counter

from sqlalchemy import Select, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.redis_client import redis_job_lock
from app.models.entities import (
    AppStatusCurrent,
    Event,
    JobRun,
    NotificationChannel,
    WatchedApp,
    WatchedPublisher,
)
from app.schemas.common import EventTypeEnum, JobNameEnum, PublisherDiscoveryResult, StoreEnum, StoreFetchResult
from app.schemas.events import JobRunResponse
from app.schemas.watch import (
    AppStatusSummary,
    PaginatedResponse,
    WatchedAppCreate,
    WatchedAppUpdate,
    WatchedAppWithStatus,
    WatchedPublisherCreate,
    WatchedPublisherRead,
    WatchedPublisherUpdate,
)
from app.services.diff_engine import DiffEngine
from app.services.notifiers.feishu import FeishuNotifier
from app.services.publisher_discovery import PublisherDiscoveryService
from app.services.store_clients.app_store import AppStoreClient
from app.services.store_clients.google_play import GooglePlayClient
from app.services.store_clients.http_client import get_global_stats, reset_global_stats

logger = logging.getLogger(__name__)


class MonitoringService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()
        self.diff_engine = DiffEngine()
        self.publisher_discovery = PublisherDiscoveryService()
        self.google_play_client = GooglePlayClient()
        self.app_store_client = AppStoreClient()

    async def ensure_default_notification_channel(self) -> None:
        if not self.settings.feishu_webhook_url:
            return

        existing = await self.session.scalar(
            select(NotificationChannel).where(NotificationChannel.name == "default-feishu")
        )
        if existing:
            if existing.webhook_url != self.settings.feishu_webhook_url or existing.secret != self.settings.feishu_secret:
                existing.webhook_url = self.settings.feishu_webhook_url
                existing.secret = self.settings.feishu_secret
                existing.enabled = True
                await self.session.commit()
            return

        self.session.add(
            NotificationChannel(
                channel_type="feishu",
                name="default-feishu",
                webhook_url=self.settings.feishu_webhook_url,
                secret=self.settings.feishu_secret,
                enabled=True,
                config_json={},
            )
        )
        await self.session.commit()

    async def create_watched_app(self, payload: WatchedAppCreate) -> WatchedApp:
        self._validate_app_payload(payload)
        query = select(WatchedApp).where(WatchedApp.store == payload.store.value)
        if payload.store == StoreEnum.GOOGLE_PLAY:
            query = query.where(WatchedApp.package_name == payload.package_name)
        elif payload.bundle_id:
            query = query.where(WatchedApp.bundle_id == payload.bundle_id)
        else:
            query = query.where(WatchedApp.app_id == payload.app_id)

        existing = await self.session.scalar(query)
        if existing:
            return existing

        watched_app = WatchedApp(
            store=payload.store.value,
            package_name=payload.package_name,
            bundle_id=payload.bundle_id,
            app_id=payload.app_id,
            display_name=payload.display_name,
            regions=payload.regions or self.settings.normalized_regions,
            monitoring_enabled=True,
            auto_added=False,
            notify_on_version_update=payload.notify_on_version_update,
            check_interval_minutes=payload.check_interval_minutes,
            tags=payload.tags,
        )
        self.session.add(watched_app)
        await self.session.commit()
        await self.session.refresh(watched_app)
        return watched_app

    async def list_watched_apps(self) -> list[WatchedApp]:
        result = await self.session.scalars(select(WatchedApp).order_by(desc(WatchedApp.created_at)))
        return list(result.all())

    async def list_watched_apps_paged(
        self, *, page: int = 1, page_size: int = 20, store: str | None = None,
        q: str | None = None, tag: str | None = None,
    ) -> PaginatedResponse[WatchedAppWithStatus]:
        import math
        from sqlalchemy import or_

        base_filter = []
        if store and store in {e.value for e in StoreEnum}:
            base_filter.append(WatchedApp.store == store)
        if q:
            pattern = f"%{q}%"
            base_filter.append(
                or_(
                    WatchedApp.display_name.ilike(pattern),
                    WatchedApp.package_name.ilike(pattern),
                    WatchedApp.bundle_id.ilike(pattern),
                    WatchedApp.app_id.ilike(pattern),
                )
            )
        if tag:
            base_filter.append(WatchedApp.tags.contains([tag]))

        count_q = select(func.count()).select_from(WatchedApp)
        list_q = select(WatchedApp).order_by(desc(WatchedApp.created_at))
        for cond in base_filter:
            count_q = count_q.where(cond)
            list_q = list_q.where(cond)

        total = await self.session.scalar(count_q) or 0
        total_pages = max(1, math.ceil(total / page_size))
        offset = (page - 1) * page_size

        apps = list(
            (
                await self.session.scalars(
                    list_q.offset(offset).limit(page_size)
                )
            ).all()
        )

        app_ids = [app.id for app in apps]
        statuses = list(
            (
                await self.session.scalars(
                    select(AppStatusCurrent).where(AppStatusCurrent.watched_app_id.in_(app_ids))
                )
            ).all()
        ) if app_ids else []
        status_map = {s.watched_app_id: s for s in statuses}

        items: list[WatchedAppWithStatus] = []
        for app in apps:
            app_data = WatchedAppWithStatus.model_validate(app)
            raw_status = status_map.get(app.id)
            if raw_status:
                app_data.status = AppStatusSummary.model_validate(raw_status)
            items.append(app_data)

        return PaginatedResponse[WatchedAppWithStatus](
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def update_watched_app(self, app_id: str, payload: WatchedAppUpdate) -> WatchedApp:
        watched_app = await self.session.get(WatchedApp, app_id)
        if not watched_app:
            raise LookupError("Watched app not found")

        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(watched_app, field, value)

        await self.session.commit()
        await self.session.refresh(watched_app)
        return watched_app

    async def delete_watched_app(self, app_id: str) -> None:
        watched_app = await self.session.get(WatchedApp, app_id)
        if not watched_app:
            raise LookupError("Watched app not found")
        await self.session.delete(watched_app)
        await self.session.commit()

    async def create_watched_publisher(self, payload: WatchedPublisherCreate) -> WatchedPublisher:
        query = select(WatchedPublisher).where(
            WatchedPublisher.store == payload.store.value,
            WatchedPublisher.publisher_name == payload.publisher_name,
        )
        existing = await self.session.scalar(query)
        if existing:
            return existing

        watched_publisher = WatchedPublisher(
            store=payload.store.value,
            publisher_name=payload.publisher_name,
            publisher_ref=payload.publisher_ref,
            publisher_url=payload.publisher_url,
            regions=payload.regions or self.settings.normalized_regions,
            monitoring_enabled=True,
            auto_add_apps=payload.auto_add_apps,
            auto_added_notify_on_version_update=payload.auto_added_notify_on_version_update,
        )
        self.session.add(watched_publisher)
        await self.session.commit()
        await self.session.refresh(watched_publisher)
        return watched_publisher

    async def list_watched_publishers(self) -> list[WatchedPublisher]:
        result = await self.session.scalars(select(WatchedPublisher).order_by(desc(WatchedPublisher.created_at)))
        return list(result.all())

    async def list_watched_publishers_paged(
        self, *, page: int = 1, page_size: int = 20
    ) -> PaginatedResponse[WatchedPublisherRead]:
        import math

        total = await self.session.scalar(select(func.count()).select_from(WatchedPublisher)) or 0
        total_pages = max(1, math.ceil(total / page_size))
        offset = (page - 1) * page_size

        publishers = list(
            (
                await self.session.scalars(
                    select(WatchedPublisher).order_by(desc(WatchedPublisher.created_at)).offset(offset).limit(page_size)
                )
            ).all()
        )

        items = [WatchedPublisherRead.model_validate(p) for p in publishers]

        return PaginatedResponse[WatchedPublisherRead](
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def update_watched_publisher(self, publisher_id: str, payload: WatchedPublisherUpdate) -> WatchedPublisher:
        watched_publisher = await self.session.get(WatchedPublisher, publisher_id)
        if not watched_publisher:
            raise LookupError("Watched publisher not found")

        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(watched_publisher, field, value)

        await self.session.commit()
        await self.session.refresh(watched_publisher)
        return watched_publisher

    async def delete_watched_publisher(self, publisher_id: str) -> None:
        watched_publisher = await self.session.get(WatchedPublisher, publisher_id)
        if not watched_publisher:
            raise LookupError("Watched publisher not found")
        await self.session.delete(watched_publisher)
        await self.session.commit()

    async def list_events(self, limit: int = 100) -> list[Event]:
        result = await self.session.scalars(select(Event).order_by(desc(Event.created_at)).limit(limit))
        return list(result.all())

    async def list_filtered_events(
        self,
        *,
        limit: int = 100,
        status: str | None = None,
        event_type: str | None = None,
        store: str | None = None,
    ) -> list[Event]:
        query = select(Event)
        if status:
            query = query.where(Event.status == status)
        if event_type:
            query = query.where(Event.event_type == event_type)
        if store:
            query = query.where(Event.store == store)
        query = query.order_by(desc(Event.created_at)).limit(limit)
        result = await self.session.scalars(query)
        return list(result.all())

    async def list_job_runs(self, limit: int = 20) -> list[JobRun]:
        result = await self.session.scalars(select(JobRun).order_by(desc(JobRun.started_at)).limit(limit))
        return list(result.all())

    async def get_dashboard_summary(self) -> dict:
        watched_apps = list(
            (
                await self.session.scalars(
                    select(WatchedApp).order_by(desc(WatchedApp.created_at)).limit(20)
                )
            ).all()
        )
        watched_publishers = list(
            (
                await self.session.scalars(
                    select(WatchedPublisher).order_by(desc(WatchedPublisher.created_at)).limit(20)
                )
            ).all()
        )
        statuses = list((await self.session.scalars(select(AppStatusCurrent))).all())
        status_by_app_id = {item.watched_app_id: item for item in statuses}
        recent_events = await self.list_filtered_events(limit=20)
        recent_job_runs = await self.list_job_runs(limit=10)

        apps_count = await self.session.scalar(select(func.count()).select_from(WatchedApp)) or 0
        publishers_count = await self.session.scalar(select(func.count()).select_from(WatchedPublisher)) or 0
        pending_events = await self.session.scalar(
            select(func.count()).select_from(Event).where(Event.status == "pending")
        ) or 0
        failed_events = await self.session.scalar(
            select(func.count()).select_from(Event).where(Event.status == "failed")
        ) or 0

        return {
            "counts": {
                "apps": apps_count,
                "publishers": publishers_count,
                "pending_events": pending_events,
                "failed_events": failed_events,
            },
            "samples": self._default_samples(),
            "apps": [
                {
                    "id": item.id,
                    "store": item.store,
                    "display_name": item.display_name,
                    "package_name": item.package_name,
                    "bundle_id": item.bundle_id,
                    "app_id": item.app_id,
                    "regions": item.regions,
                    "monitoring_enabled": item.monitoring_enabled,
                    "auto_added": item.auto_added,
                    "notify_on_version_update": item.notify_on_version_update,
                    "check_interval_minutes": item.check_interval_minutes,
                    "created_at": item.created_at.isoformat(),
                    "updated_at": item.updated_at.isoformat(),
                    "status": self._serialize_app_status(status_by_app_id.get(item.id)),
                }
                for item in watched_apps
            ],
            "publishers": [
                {
                    "id": item.id,
                    "store": item.store,
                    "publisher_name": item.publisher_name,
                    "publisher_ref": item.publisher_ref,
                    "publisher_url": item.publisher_url,
                    "regions": item.regions,
                    "monitoring_enabled": item.monitoring_enabled,
                    "auto_add_apps": item.auto_add_apps,
                    "auto_added_notify_on_version_update": item.auto_added_notify_on_version_update,
                    "created_at": item.created_at.isoformat(),
                    "updated_at": item.updated_at.isoformat(),
                }
                for item in watched_publishers
            ],
            "events": [
                {
                    "id": event.id,
                    "event_type": event.event_type,
                    "store": event.store,
                    "status": event.status,
                    "region": event.region,
                    "payload": event.payload,
                    "created_at": event.created_at.isoformat(),
                    "sent_at": event.sent_at.isoformat() if event.sent_at else None,
                    "last_error": event.last_error,
                }
                for event in recent_events
            ],
            "job_runs": [
                {
                    "id": job.id,
                    "job_name": job.job_name,
                    "status": job.status,
                    "started_at": job.started_at.isoformat(),
                    "finished_at": job.finished_at.isoformat() if job.finished_at else None,
                    "duration_ms": job.duration_ms,
                    "detail_json": job.detail_json,
                    "error_text": job.error_text,
                }
                for job in recent_job_runs
            ],
        }

    async def execute_job(self, job_name: JobNameEnum) -> JobRunResponse:
        if job_name == JobNameEnum.MONITOR_APPS:
            detail = await self.run_app_checks()
        elif job_name == JobNameEnum.DISCOVER_PUBLISHERS:
            detail = await self.run_publisher_discovery()
        elif job_name == JobNameEnum.DELIVER_NOTIFICATIONS:
            detail = await self.dispatch_pending_events()
        elif job_name == JobNameEnum.GENERATE_DIGEST:
            detail = await self.generate_digest()
        else:
            raise ValueError(f"Unsupported job: {job_name}")
        return JobRunResponse(job_name=job_name.value, status="completed", detail=detail)

    async def run_app_checks(self) -> dict:
        async def _job() -> dict:
            stats = reset_global_stats()
            apps = list(
                (
                    await self.session.scalars(
                        select(WatchedApp).where(WatchedApp.monitoring_enabled.is_(True)).order_by(WatchedApp.created_at.asc())
                    )
                ).all()
            )
            checked = 0
            emitted = 0
            skipped = 0
            now = datetime.now(timezone.utc)
            region_batch_size = 3

            for watched_app in apps:
                status = await self.session.scalar(
                    select(AppStatusCurrent).where(AppStatusCurrent.watched_app_id == watched_app.id)
                )
                if self._should_skip_adaptive(status, watched_app, now):
                    skipped += 1
                    continue

                regions = watched_app.regions or self.settings.normalized_regions
                for i in range(0, len(regions), region_batch_size):
                    batch = regions[i : i + region_batch_size]
                    for region in batch:
                        result = await self._fetch_app_result(watched_app=watched_app, region=region)
                        events = await self.diff_engine.apply_app_result(self.session, watched_app, result)
                        checked += 1
                        emitted += len(events)
                    if i + region_batch_size < len(regions):
                        await asyncio.sleep(1.0)
                await self.session.commit()
            alerts = await self._check_fetch_health_and_alert(stats)
            return {
                "checks": checked,
                "events": emitted,
                "skipped_adaptive": skipped,
                "health_alerts": alerts,
                "fetch_stats": stats.to_dict(),
            }

        return await self._run_job_with_audit(JobNameEnum.MONITOR_APPS.value, _job)

    async def _check_fetch_health_and_alert(self, stats: StoreStats) -> int:
        """Check per-store health metrics and emit alert events if thresholds exceeded."""
        alert_count = 0
        min_req = self.settings.store_alert_min_requests
        rl_pct = self.settings.store_alert_rate_limit_pct
        err_pct = self.settings.store_alert_error_pct

        for store_name, fs in stats.stores.items():
            if fs.requests < min_req:
                continue

            rl_rate = round((fs.rate_limited + fs.forbidden) / fs.requests * 100, 1)
            err_rate = round(fs.errors / fs.requests * 100, 1)
            success_rate = round(fs.successes / fs.requests * 100, 1)

            if rl_rate >= rl_pct:
                event = Event(
                    event_type="store_rate_limit_alert",
                    store=store_name,
                    payload={
                        "alert": "rate_limit_threshold_exceeded",
                        "rate_limited_pct": rl_rate,
                        "threshold_pct": rl_pct,
                        "requests": fs.requests,
                        "rate_limited": fs.rate_limited,
                        "forbidden": fs.forbidden,
                        "cooldowns": fs.cooldowns_triggered,
                        "success_rate_pct": success_rate,
                    },
                    dedupe_key=f"store-rl-alert:{store_name}:{datetime.now(timezone.utc).strftime('%Y%m%d%H')}",
                    status="pending",
                    created_at=datetime.now(timezone.utc),
                )
                self.session.add(event)
                alert_count += 1
                logger.warning(
                    "Rate-limit alert for %s: %.1f%% (threshold %d%%)",
                    store_name, rl_rate, rl_pct,
                )

            if err_rate >= err_pct:
                event = Event(
                    event_type="store_error_alert",
                    store=store_name,
                    payload={
                        "alert": "error_threshold_exceeded",
                        "error_pct": err_rate,
                        "threshold_pct": err_pct,
                        "requests": fs.requests,
                        "errors": fs.errors,
                        "success_rate_pct": success_rate,
                    },
                    dedupe_key=f"store-err-alert:{store_name}:{datetime.now(timezone.utc).strftime('%Y%m%d%H')}",
                    status="pending",
                    created_at=datetime.now(timezone.utc),
                )
                self.session.add(event)
                alert_count += 1
                logger.warning(
                    "Error alert for %s: %.1f%% (threshold %d%%)",
                    store_name, err_rate, err_pct,
                )

        if alert_count:
            await self.session.commit()
        return alert_count

    def _should_skip_adaptive(self, status: AppStatusCurrent | None, app: WatchedApp, now: datetime) -> bool:
        if not status or not status.last_checked_at:
            return False
        threshold = self.settings.store_adaptive_no_change_threshold
        no_change = status.consecutive_no_change or 0
        if no_change < threshold:
            return False
        multiplier = min(
            1 + (no_change - threshold) // threshold,
            self.settings.store_adaptive_max_interval_multiplier,
        )
        base_interval = app.check_interval_minutes or self.settings.app_monitor_interval_minutes
        effective_minutes = base_interval * multiplier
        next_check = status.last_checked_at + timedelta(minutes=effective_minutes)
        if now < next_check:
            logger.debug(
                "Adaptive skip: app=%s no_change=%d multiplier=%dx next=%s",
                app.display_name or app.id,
                no_change,
                multiplier,
                next_check.isoformat(),
            )
            return True
        return False

    async def run_publisher_discovery(self) -> dict:
        async def _job() -> dict:
            stats = reset_global_stats()
            publishers = list(
                (
                    await self.session.scalars(
                        select(WatchedPublisher)
                        .where(WatchedPublisher.monitoring_enabled.is_(True))
                        .order_by(WatchedPublisher.created_at.asc())
                    )
                ).all()
            )
            checked = 0
            emitted = 0
            region_batch_size = 2
            for publisher in publishers:
                regions = publisher.regions or self.settings.normalized_regions
                for i in range(0, len(regions), region_batch_size):
                    batch = regions[i : i + region_batch_size]
                    for region in batch:
                        result = await self._discover_publisher_result(publisher=publisher, region=region)
                        events = await self.publisher_discovery.apply_discovery_result(
                            self.session,
                            publisher,
                            region,
                            result.apps,
                            result.raw_payload,
                        )
                        checked += 1
                        emitted += len(events)
                    if i + region_batch_size < len(regions):
                        await asyncio.sleep(1.5)
                await self.session.commit()
            alerts = await self._check_fetch_health_and_alert(stats)
            return {"checks": checked, "events": emitted, "health_alerts": alerts, "fetch_stats": stats.to_dict()}

        return await self._run_job_with_audit(JobNameEnum.DISCOVER_PUBLISHERS.value, _job)

    async def dispatch_pending_events(self) -> dict:
        async def _job() -> dict:
            channels = await self.session.scalars(
                select(NotificationChannel).where(NotificationChannel.enabled.is_(True))
            )
            active_channels = list(channels.all())
            if not active_channels:
                return {"pending": 0, "sent": 0, "suppressed": 0}

            pending_events = await self.session.scalars(
                select(Event).where(Event.status == "pending").order_by(Event.created_at.asc()).limit(200)
            )
            sent = 0
            suppressed = 0
            for event in pending_events.all():
                if await self._is_duplicate_event(event):
                    event.status = "suppressed"
                    suppressed += 1
                    await self.session.commit()
                    continue

                card = self._format_event_card(event)
                try:
                    for channel in active_channels:
                        if channel.channel_type != "feishu":
                            continue
                        notifier = FeishuNotifier(
                            webhook_url=channel.webhook_url,
                            secret=channel.secret,
                            timeout=self.settings.request_timeout_seconds,
                        )
                        await notifier.send_card(card)
                    event.status = "sent"
                    event.sent_at = datetime.now(timezone.utc)
                    event.last_error = None
                    sent += 1
                except Exception as exc:  # noqa: BLE001
                    event.status = "failed"
                    event.last_error = str(exc)
                finally:
                    await self.session.commit()

            return {"pending": sent + suppressed, "sent": sent, "suppressed": suppressed}

        return await self._run_job_with_audit(JobNameEnum.DELIVER_NOTIFICATIONS.value, _job)

    async def generate_digest(self) -> dict:
        async def _job() -> dict:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

            events_q = await self.session.scalars(
                select(Event).where(Event.created_at >= cutoff).order_by(Event.created_at.asc())
            )
            all_events = list(events_q.all())

            type_counts: dict[str, int] = {}
            for ev in all_events:
                label = self._EVENT_TYPE_LABELS.get(ev.event_type, ev.event_type)
                type_counts[label] = type_counts.get(label, 0) + 1

            event_lines = [f"- {label}: **{count}** 条" for label, count in type_counts.items()]
            event_summary = "\n".join(event_lines) if event_lines else "- 无事件"

            health_summary = await self._build_health_summary(cutoff)

            elements: list[dict] = [
                {"tag": "div", "text": {"tag": "lark_md", "content": f"**事件汇总** (共 {len(all_events)} 条)\n{event_summary}"}},
                {"tag": "hr"},
                {"tag": "div", "text": {"tag": "lark_md", "content": health_summary}},
            ]

            card = {
                "header": {
                    "title": {"tag": "plain_text", "content": f"监控日报 | 过去 24h"},
                    "template": "indigo",
                },
                "elements": elements,
            }

            channels = await self.session.scalars(
                select(NotificationChannel).where(NotificationChannel.enabled.is_(True))
            )
            sent = False
            for channel in channels.all():
                if channel.channel_type != "feishu":
                    continue
                notifier = FeishuNotifier(
                    webhook_url=channel.webhook_url,
                    secret=channel.secret,
                    timeout=self.settings.request_timeout_seconds,
                )
                await notifier.send_card(card)
                sent = True

            return {"events": len(all_events), "sent": sent}

        return await self._run_job_with_audit(JobNameEnum.GENERATE_DIGEST.value, _job)

    async def _build_health_summary(self, cutoff: datetime) -> str:
        job_runs = list(
            (
                await self.session.scalars(
                    select(JobRun).where(
                        JobRun.started_at >= cutoff,
                        JobRun.job_name.in_(["monitor_apps", "discover_publishers"]),
                    ).order_by(desc(JobRun.started_at))
                )
            ).all()
        )

        if not job_runs:
            return "**采集健康** ✅\n- 过去 24h 无采集作业运行"

        total_runs = len(job_runs)
        completed = sum(1 for j in job_runs if j.status == "completed")
        failed = sum(1 for j in job_runs if j.status == "failed")

        total_requests = 0
        total_429 = 0
        total_403 = 0
        total_errors = 0
        total_cooldowns = 0
        for j in job_runs:
            fs = (j.detail_json or {}).get("fetch_stats", {})
            for store_stats in fs.values():
                total_requests += store_stats.get("requests", 0)
                total_429 += store_stats.get("rate_limited", 0)
                total_403 += store_stats.get("forbidden", 0)
                total_errors += store_stats.get("errors", 0)
                total_cooldowns += store_stats.get("cooldowns_triggered", 0)

        success_pct = round((total_requests - total_429 - total_403 - total_errors) / max(total_requests, 1) * 100, 1)
        status_icon = "✅" if success_pct >= 95 else "⚠️" if success_pct >= 80 else "🔴"

        lines = [
            f"**采集健康** {status_icon}",
            f"- 作业运行: {total_runs} 次 (成功 {completed}, 失败 {failed})",
            f"- 总请求: {total_requests}",
            f"- 成功率: {success_pct}%",
            f"- 429/限流: {total_429}",
            f"- 403/禁止: {total_403}",
            f"- 错误: {total_errors}",
        ]
        if total_cooldowns:
            lines.append(f"- 冷却触发: {total_cooldowns} 次")

        return "\n".join(lines)

    async def list_events_paged(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        event_type: str | None = None,
        store: str | None = None,
        q: str | None = None,
    ) -> PaginatedResponse:
        import math
        from sqlalchemy import or_

        base_q = select(Event)
        count_q = select(func.count()).select_from(Event)

        filters = []
        if status:
            filters.append(Event.status == status)
        if event_type:
            filters.append(Event.event_type == event_type)
        if store:
            filters.append(Event.store == store)
        if q:
            pattern = f"%{q}%"
            filters.append(
                or_(
                    Event.event_type.ilike(pattern),
                    Event.store.ilike(pattern),
                )
            )

        for f in filters:
            base_q = base_q.where(f)
            count_q = count_q.where(f)

        total = await self.session.scalar(count_q) or 0
        total_pages = max(1, math.ceil(total / page_size))
        offset = (page - 1) * page_size

        events_result = await self.session.scalars(
            base_q.order_by(desc(Event.created_at)).offset(offset).limit(page_size)
        )
        items = [
            {
                "id": ev.id,
                "event_type": ev.event_type,
                "store": ev.store,
                "status": ev.status,
                "region": ev.region,
                "payload": ev.payload,
                "created_at": ev.created_at.isoformat(),
                "sent_at": ev.sent_at.isoformat() if ev.sent_at else None,
                "last_error": ev.last_error,
            }
            for ev in events_result.all()
        ]

        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def _fetch_app_result(self, watched_app: WatchedApp, region: str) -> StoreFetchResult:
        try:
            if watched_app.store == StoreEnum.GOOGLE_PLAY.value:
                if not watched_app.package_name:
                    raise ValueError("Google Play monitor requires package_name")
                return await self.google_play_client.fetch_app(package_name=watched_app.package_name, region=region)
            if watched_app.store == StoreEnum.APP_STORE.value:
                return await self.app_store_client.fetch_app(
                    region=region,
                    bundle_id=watched_app.bundle_id,
                    app_id=watched_app.app_id,
                )
            raise ValueError(f"Unsupported store {watched_app.store}")
        except Exception as exc:  # noqa: BLE001
            return StoreFetchResult(
                store=StoreEnum(watched_app.store),
                region=region,
                fetch_status="error",
                metadata={"error": str(exc)},
                raw_payload={"error": str(exc)},
                observed_at=datetime.now(timezone.utc),
            )

    async def _discover_publisher_result(self, publisher: WatchedPublisher, region: str):
        try:
            if publisher.store == StoreEnum.GOOGLE_PLAY.value:
                return await self.google_play_client.discover_publisher(
                    region=region,
                    publisher_name=publisher.publisher_name,
                    publisher_url=publisher.publisher_url,
                )
            if publisher.store == StoreEnum.APP_STORE.value:
                return await self.app_store_client.discover_publisher(
                    region=region,
                    publisher_name=publisher.publisher_name,
                )
            raise ValueError(f"Unsupported store {publisher.store}")
        except Exception:  # noqa: BLE001
            return PublisherDiscoveryResult(
                store=StoreEnum(publisher.store),
                region=region,
                apps=[],
                raw_payload=[],
                observed_at=datetime.now(timezone.utc),
            )

    async def _is_duplicate_event(self, event: Event) -> bool:
        if not event.dedupe_key:
            return False
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=self.settings.event_dedupe_window_minutes)
        query: Select[tuple[Event]] = select(Event).where(
            Event.dedupe_key == event.dedupe_key,
            Event.status == "sent",
            Event.created_at >= cutoff,
            Event.id != event.id,
        )
        existing = await self.session.scalar(query)
        return existing is not None

    def _format_event_text(self, event: Event) -> str:
        payload = event.payload or {}
        app = payload.get("app") or {}
        identity = (
            payload.get("display_name")
            or app.get("name")
            or payload.get("package_name")
            or payload.get("bundle_id")
            or payload.get("app_id")
        )
        if event.event_type == EventTypeEnum.APP_VERSION_UPDATED.value:
            lines = [
                "事件: 应用版本更新",
                f"商店: {event.store}",
                f"对象: {identity}",
                f"版本: {payload.get('old_version') or '-'} -> {payload.get('new_version') or payload.get('version') or '-'}",
            ]
            if event.region:
                lines.append(f"区域: {event.region}")
            if payload.get("developer_name"):
                lines.append(f"开发者: {payload['developer_name']}")
            if payload.get("url"):
                lines.append(f"链接: {payload['url']}")
            return "\n".join(lines)

        lines = [
            f"事件: {event.event_type}",
            f"商店: {event.store}",
            f"对象: {identity}",
        ]
        if event.region:
            lines.append(f"区域: {event.region}")
        if payload.get("developer_name"):
            lines.append(f"开发者: {payload['developer_name']}")
        if payload.get("publisher_name"):
            lines.append(f"厂商: {payload['publisher_name']}")
        if payload.get("url") or app.get("url"):
            lines.append(f"链接: {payload.get('url') or app.get('url')}")
        if payload.get("visible_regions"):
            lines.append(f"可见区域: {', '.join(payload['visible_regions'])}")
        return "\n".join(lines)

    _EVENT_TYPE_LABELS = {
        "app_visible_first_seen": "应用首次上架",
        "app_visible_region_added": "新增上架区域",
        "app_removed_from_store": "应用下架",
        "app_removed_from_region": "区域下架",
        "app_version_updated": "版本更新",
        "app_rating_changed": "评分变动",
        "app_release_notes_changed": "更新日志变更",
        "publisher_new_game_detected": "厂商新游上架",
        "metadata_changed_significantly": "元数据变更",
        "monitor_failed_repeatedly": "监控连续失败",
        "store_rate_limit_alert": "商店限流告警",
        "store_error_alert": "商店错误告警",
    }

    def _format_event_card(self, event: Event) -> dict:
        payload = event.payload or {}
        app = payload.get("app") or {}

        if event.event_type in ("store_rate_limit_alert", "store_error_alert"):
            identity = payload.get("alert", "系统告警")
        else:
            identity = (
                payload.get("display_name")
                or app.get("name")
                or payload.get("package_name")
                or payload.get("bundle_id")
                or payload.get("app_id")
                or "未知"
            )
        event_label = self._EVENT_TYPE_LABELS.get(event.event_type, event.event_type)
        store_label = "Google Play" if event.store == "google_play" else "App Store"

        fields: list[dict] = []
        fields.append({"is_short": True, "text": {"tag": "lark_md", "content": f"**商店**\n{store_label}"}})
        if event.region:
            fields.append({"is_short": True, "text": {"tag": "lark_md", "content": f"**区域**\n{event.region}"}})

        if event.event_type == EventTypeEnum.APP_VERSION_UPDATED.value:
            old_v = payload.get("old_version") or "-"
            new_v = payload.get("new_version") or payload.get("version") or "-"
            fields.append({"is_short": True, "text": {"tag": "lark_md", "content": f"**版本**\n{old_v} → {new_v}"}})

        if event.event_type == EventTypeEnum.APP_RATING_CHANGED.value:
            old_r = payload.get("old_rating")
            new_r = payload.get("new_rating")
            old_str = f"{old_r:.2f}" if old_r is not None else "-"
            new_str = f"{new_r:.2f}" if new_r is not None else "-"
            fields.append({"is_short": True, "text": {"tag": "lark_md", "content": f"**评分**\n{old_str} → {new_str}"}})
            rc = payload.get("rating_count")
            if rc is not None:
                fields.append({"is_short": True, "text": {"tag": "lark_md", "content": f"**评分人数**\n{rc:,}"}})

        if event.event_type in ("store_rate_limit_alert", "store_error_alert"):
            if payload.get("rate_limited_pct") is not None:
                fields.append({"is_short": True, "text": {"tag": "lark_md", "content": f"**限流率**\n{payload['rate_limited_pct']}%"}})
            if payload.get("error_pct") is not None:
                fields.append({"is_short": True, "text": {"tag": "lark_md", "content": f"**错误率**\n{payload['error_pct']}%"}})
            if payload.get("requests") is not None:
                fields.append({"is_short": True, "text": {"tag": "lark_md", "content": f"**请求数**\n{payload['requests']}"}})
            if payload.get("success_rate_pct") is not None:
                fields.append({"is_short": True, "text": {"tag": "lark_md", "content": f"**成功率**\n{payload['success_rate_pct']}%"}})
            if payload.get("cooldowns"):
                fields.append({"is_short": True, "text": {"tag": "lark_md", "content": f"**冷却触发**\n{payload['cooldowns']} 次"}})

        if payload.get("developer_name"):
            fields.append({"is_short": True, "text": {"tag": "lark_md", "content": f"**开发者**\n{payload['developer_name']}"}})
        if payload.get("publisher_name"):
            fields.append({"is_short": True, "text": {"tag": "lark_md", "content": f"**厂商**\n{payload['publisher_name']}"}})
        if payload.get("visible_regions"):
            fields.append({"is_short": False, "text": {"tag": "lark_md", "content": f"**可见区域**\n{', '.join(payload['visible_regions'])}"}})

        elements: list[dict] = [{"tag": "div", "fields": fields}]

        if event.event_type == EventTypeEnum.APP_RELEASE_NOTES_CHANGED.value and payload.get("release_notes"):
            snippet = payload["release_notes"][:200]
            if len(payload["release_notes"]) > 200:
                snippet += "..."
            elements.append({"tag": "div", "text": {"tag": "lark_md", "content": f"**更新日志**\n{snippet}"}})

        url = payload.get("url") or app.get("url")
        if url:
            elements.append({
                "tag": "action",
                "actions": [{
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "查看商店"},
                    "type": "primary",
                    "url": url,
                }],
            })

        icon_url = payload.get("metadata", {}).get("icon_url") or payload.get("metadata", {}).get("image")
        title_elements: list[dict] = [{"tag": "plain_text", "content": f"{event_label} | {identity}"}]

        header: dict = {
            "title": {"tag": "plain_text", "content": f"{event_label} | {identity}"},
            "template": "orange" if "alert" in event.event_type else "blue" if "visible" in event.event_type else "red" if "removed" in event.event_type or "failed" in event.event_type else "turquoise",
        }
        if icon_url:
            header["icon"] = {"tag": "custom_icon", "img_key": icon_url}

        return {
            "header": header,
            "elements": elements,
        }

    def _serialize_app_status(self, status: AppStatusCurrent | None) -> dict | None:
        if not status:
            return None
        return {
            "visible_regions": status.visible_regions,
            "invisible_regions": status.invisible_regions,
            "last_seen_visible_at": status.last_seen_visible_at.isoformat() if status.last_seen_visible_at else None,
            "last_seen_invisible_at": (
                status.last_seen_invisible_at.isoformat() if status.last_seen_invisible_at else None
            ),
            "last_checked_at": status.last_checked_at.isoformat() if status.last_checked_at else None,
            "last_title": status.last_title,
            "last_developer_name": status.last_developer_name,
            "last_version": status.last_version,
            "last_category": status.last_category,
            "last_url": status.last_url,
            "last_icon_url": status.last_icon_url,
            "last_rating": status.last_rating,
            "last_rating_count": status.last_rating_count,
            "last_price": status.last_price,
            "last_release_notes": status.last_release_notes,
            "last_file_size": status.last_file_size,
            "last_content_rating": status.last_content_rating,
            "last_store_updated_at": status.last_store_updated_at,
        }

    def _default_samples(self) -> dict:
        return {
            "google_play": {
                "store": "google_play",
                "display_name": "Clash of Clans",
                "package_name": "com.supercell.clashofclans",
                "regions": ["US", "JP", "KR"],
                "notify_on_version_update": True,
            },
            "app_store": {
                "store": "app_store",
                "display_name": "Clash of Clans",
                "bundle_id": "com.supercell.magic",
                "app_id": "529479190",
                "regions": ["US", "JP", "KR"],
                "notify_on_version_update": True,
            },
            "publisher": {
                "store": "app_store",
                "publisher_name": "Supercell",
                "regions": ["US", "JP"],
                "auto_add_apps": True,
                "auto_added_notify_on_version_update": True,
            },
        }

    async def _run_job_with_audit(self, job_name: str, handler) -> dict:
        async with redis_job_lock(f"job-lock:{job_name}", self.settings.job_lock_ttl_seconds) as acquired:
            if not acquired:
                job_run = JobRun(
                    job_name=job_name,
                    status="skipped",
                    started_at=datetime.now(timezone.utc),
                    finished_at=datetime.now(timezone.utc),
                    duration_ms=0,
                    detail_json={"reason": "job lock not acquired"},
                )
                self.session.add(job_run)
                await self.session.commit()
                return {"skipped": True, "reason": "job lock not acquired"}

            started_at = datetime.now(timezone.utc)
            timer = perf_counter()
            job_run = JobRun(job_name=job_name, status="running", started_at=started_at, detail_json={})
            self.session.add(job_run)
            await self.session.commit()
            try:
                detail = await handler()
                job_run.status = "completed"
                job_run.detail_json = detail
                return detail
            except Exception as exc:  # noqa: BLE001
                await self.session.rollback()
                job_run.status = "failed"
                job_run.error_text = str(exc)
                raise
            finally:
                job_run.finished_at = datetime.now(timezone.utc)
                job_run.duration_ms = int((perf_counter() - timer) * 1000)
                self.session.add(job_run)
                await self.session.commit()

    def _validate_app_payload(self, payload: WatchedAppCreate) -> None:
        if payload.store == StoreEnum.GOOGLE_PLAY and not payload.package_name:
            raise ValueError("Google Play monitor requires package_name")
        if payload.store == StoreEnum.APP_STORE and not (payload.bundle_id or payload.app_id):
            raise ValueError("App Store monitor requires bundle_id or app_id")

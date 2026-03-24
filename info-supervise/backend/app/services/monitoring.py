from __future__ import annotations

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
        )
        self.session.add(watched_app)
        await self.session.commit()
        await self.session.refresh(watched_app)
        return watched_app

    async def list_watched_apps(self) -> list[WatchedApp]:
        result = await self.session.scalars(select(WatchedApp).order_by(desc(WatchedApp.created_at)))
        return list(result.all())

    async def list_watched_apps_paged(
        self, *, page: int = 1, page_size: int = 20
    ) -> PaginatedResponse[WatchedAppWithStatus]:
        import math

        total = await self.session.scalar(select(func.count()).select_from(WatchedApp)) or 0
        total_pages = max(1, math.ceil(total / page_size))
        offset = (page - 1) * page_size

        apps = list(
            (
                await self.session.scalars(
                    select(WatchedApp).order_by(desc(WatchedApp.created_at)).offset(offset).limit(page_size)
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
        else:
            raise ValueError(f"Unsupported job: {job_name}")
        return JobRunResponse(job_name=job_name.value, status="completed", detail=detail)

    async def run_app_checks(self) -> dict:
        async def _job() -> dict:
            apps = await self.session.scalars(
                select(WatchedApp).where(WatchedApp.monitoring_enabled.is_(True)).order_by(WatchedApp.created_at.asc())
            )
            checked = 0
            emitted = 0
            for watched_app in apps.all():
                for region in watched_app.regions or self.settings.normalized_regions:
                    result = await self._fetch_app_result(watched_app=watched_app, region=region)
                    events = await self.diff_engine.apply_app_result(self.session, watched_app, result)
                    checked += 1
                    emitted += len(events)
                await self.session.commit()
            return {"checks": checked, "events": emitted}

        return await self._run_job_with_audit(JobNameEnum.MONITOR_APPS.value, _job)

    async def run_publisher_discovery(self) -> dict:
        async def _job() -> dict:
            publishers = await self.session.scalars(
                select(WatchedPublisher)
                .where(WatchedPublisher.monitoring_enabled.is_(True))
                .order_by(WatchedPublisher.created_at.asc())
            )
            checked = 0
            emitted = 0
            for publisher in publishers.all():
                for region in publisher.regions or self.settings.normalized_regions:
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
                await self.session.commit()
            return {"checks": checked, "events": emitted}

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

                message = self._format_event_text(event)
                try:
                    for channel in active_channels:
                        if channel.channel_type != "feishu":
                            continue
                        notifier = FeishuNotifier(
                            webhook_url=channel.webhook_url,
                            secret=channel.secret,
                            timeout=self.settings.request_timeout_seconds,
                        )
                        await notifier.send_text(message)
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

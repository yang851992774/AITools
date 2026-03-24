from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Event, PublisherSnapshot, WatchedApp, WatchedPublisher
from app.schemas.common import EventTypeEnum, PublisherAppRecord, StoreEnum


class PublisherDiscoveryService:
    async def apply_discovery_result(
        self,
        session: AsyncSession,
        watched_publisher: WatchedPublisher,
        region: str,
        apps: list[PublisherAppRecord],
        raw_payload: list[dict],
    ) -> list[Event]:
        previous_snapshot = await session.scalar(
            select(PublisherSnapshot)
            .where(
                PublisherSnapshot.watched_publisher_id == watched_publisher.id,
                PublisherSnapshot.region == region,
            )
            .order_by(PublisherSnapshot.observed_at.desc())
        )
        previous_keys = set(previous_snapshot.app_keys if previous_snapshot else [])
        current_keys = {app.external_key for app in apps}

        snapshot = PublisherSnapshot(
            watched_publisher_id=watched_publisher.id,
            store=watched_publisher.store,
            region=region,
            app_keys=sorted(current_keys),
            raw_payload=raw_payload,
        )
        session.add(snapshot)

        events: list[Event] = []
        for app in apps:
            if app.external_key in previous_keys:
                continue
            event = Event(
                event_type=EventTypeEnum.PUBLISHER_NEW_GAME_DETECTED.value,
                store=watched_publisher.store,
                watched_publisher_id=watched_publisher.id,
                region=region,
                dedupe_key=f"publisher_new_game:{watched_publisher.id}:{region}:{app.external_key}",
                payload={
                    "publisher_name": watched_publisher.publisher_name,
                    "region": region,
                    "app": app.model_dump(),
                },
                status="pending",
            )
            session.add(event)
            events.append(event)
            if watched_publisher.auto_add_apps:
                await self._ensure_watched_app(session, watched_publisher, app)

        return events

    async def _ensure_watched_app(
        self,
        session: AsyncSession,
        watched_publisher: WatchedPublisher,
        app: PublisherAppRecord,
    ) -> None:
        query = select(WatchedApp).where(WatchedApp.store == watched_publisher.store)
        if watched_publisher.store == StoreEnum.GOOGLE_PLAY.value and app.package_name:
            query = query.where(WatchedApp.package_name == app.package_name)
        elif watched_publisher.store == StoreEnum.APP_STORE.value:
            if app.bundle_id:
                query = query.where(WatchedApp.bundle_id == app.bundle_id)
            elif app.app_id:
                query = query.where(WatchedApp.app_id == app.app_id)
        else:
            return

        existing = await session.scalar(query)
        if existing:
            return

        session.add(
            WatchedApp(
                store=watched_publisher.store,
                package_name=app.package_name,
                bundle_id=app.bundle_id,
                app_id=app.app_id,
                display_name=app.name,
                regions=watched_publisher.regions,
                auto_added=True,
                monitoring_enabled=True,
                notify_on_version_update=watched_publisher.auto_added_notify_on_version_update,
            )
        )

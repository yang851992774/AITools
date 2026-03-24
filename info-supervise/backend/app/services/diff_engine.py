from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.entities import AppStatusCurrent, AppStoreSnapshot, Event, WatchedApp
from app.schemas.common import EventTypeEnum, StoreFetchResult


class DiffEngine:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def apply_app_result(
        self,
        session: AsyncSession,
        watched_app: WatchedApp,
        result: StoreFetchResult,
    ) -> list[Event]:
        snapshot = AppStoreSnapshot(
            watched_app_id=watched_app.id,
            store=watched_app.store,
            region=result.region,
            is_visible=result.is_visible,
            fetch_status=result.fetch_status,
            title=result.title,
            developer_name=result.developer_name,
            version=result.version,
            category=result.category,
            url=result.url,
            metadata_json=result.metadata,
            raw_payload=result.raw_payload,
            observed_at=result.observed_at,
        )
        session.add(snapshot)

        status = await session.scalar(
            select(AppStatusCurrent).where(AppStatusCurrent.watched_app_id == watched_app.id)
        )
        if not status:
            status = AppStatusCurrent(
                watched_app_id=watched_app.id,
                store=watched_app.store,
                visible_regions=[],
                invisible_regions=[],
                region_states={},
                metadata_json={},
            )
            session.add(status)

        events: list[Event] = []
        region_states = dict(status.region_states or {})
        region_state = dict(region_states.get(result.region, {}))
        visible_regions = set(status.visible_regions or [])
        invisible_regions = set(status.invisible_regions or [])

        status.last_checked_at = result.observed_at
        region_state["last_checked_at"] = result.observed_at.isoformat()

        if result.fetch_status != "success":
            failures = int(region_state.get("consecutive_failure_count", 0)) + 1
            region_state["consecutive_failure_count"] = failures
            status.last_error_at = result.observed_at
            if failures >= self.settings.visibility_confirm_threshold:
                events.append(
                    self._build_event(
                        event_type=EventTypeEnum.MONITOR_FAILED_REPEATEDLY.value,
                        store=watched_app.store,
                        watched_app_id=watched_app.id,
                        region=result.region,
                        payload={
                            "display_name": watched_app.display_name,
                            "package_name": watched_app.package_name,
                            "bundle_id": watched_app.bundle_id,
                            "app_id": watched_app.app_id,
                            "fetch_status": result.fetch_status,
                            "failure_count": failures,
                        },
                        dedupe_key=f"failure:{watched_app.id}:{result.region}:{failures}",
                    )
                )
        else:
            region_state["consecutive_failure_count"] = 0
            old_version = status.last_version
            metadata_changed = self._has_metadata_change(status, result)
            version_updated = self._has_version_update(status, result, watched_app)
            was_visible = bool(region_state.get("visible"))

            if result.is_visible:
                region_state["visible"] = True
                region_state["consecutive_invisible_count"] = 0
                region_state["last_seen_visible_at"] = result.observed_at.isoformat()
                visible_regions.add(result.region)
                invisible_regions.discard(result.region)
                status.last_seen_visible_at = result.observed_at

                if not was_visible:
                    event_type = (
                        EventTypeEnum.APP_VISIBLE_FIRST_SEEN.value
                        if not status.visible_regions
                        else EventTypeEnum.APP_VISIBLE_REGION_ADDED.value
                    )
                    events.append(
                        self._build_event(
                            event_type=event_type,
                            store=watched_app.store,
                            watched_app_id=watched_app.id,
                            region=result.region,
                            payload=self._event_payload(watched_app, result, visible_regions),
                            dedupe_key=f"{event_type}:{watched_app.id}:{result.region}",
                        )
                    )

                if metadata_changed:
                    events.append(
                        self._build_event(
                            event_type=EventTypeEnum.METADATA_CHANGED_SIGNIFICANTLY.value,
                            store=watched_app.store,
                            watched_app_id=watched_app.id,
                            region=result.region,
                            payload=self._event_payload(watched_app, result, visible_regions),
                            dedupe_key=f"metadata:{watched_app.id}:{result.region}:{result.version or 'na'}",
                        )
                    )

                if version_updated:
                    events.append(
                        self._build_event(
                            event_type=EventTypeEnum.APP_VERSION_UPDATED.value,
                            store=watched_app.store,
                            watched_app_id=watched_app.id,
                            region=result.region,
                            payload=self._event_payload(
                                watched_app,
                                result,
                                visible_regions,
                                extra_payload={
                                    "old_version": old_version,
                                    "new_version": result.version,
                                },
                            ),
                            dedupe_key=f"version-update:{watched_app.id}:{result.version or 'na'}",
                        )
                    )
            else:
                invisible_count = int(region_state.get("consecutive_invisible_count", 0)) + 1
                region_state["consecutive_invisible_count"] = invisible_count
                region_state["visible"] = False if invisible_count >= self.settings.visibility_confirm_threshold else was_visible
                if invisible_count >= self.settings.visibility_confirm_threshold and result.region in visible_regions:
                    visible_regions.discard(result.region)
                    invisible_regions.add(result.region)
                    status.last_seen_invisible_at = result.observed_at
                    event_type = (
                        EventTypeEnum.APP_REMOVED_FROM_STORE.value
                        if not visible_regions
                        else EventTypeEnum.APP_REMOVED_FROM_REGION.value
                    )
                    events.append(
                        self._build_event(
                            event_type=event_type,
                            store=watched_app.store,
                            watched_app_id=watched_app.id,
                            region=result.region,
                            payload=self._event_payload(watched_app, result, visible_regions),
                            dedupe_key=f"{event_type}:{watched_app.id}:{result.region}",
                        )
                    )

            if result.title:
                status.last_title = result.title
            if result.developer_name:
                status.last_developer_name = result.developer_name
            if result.version:
                status.last_version = result.version
            if result.category:
                status.last_category = result.category
            if result.url:
                status.last_url = result.url
            if result.icon_url:
                status.last_icon_url = result.icon_url
            status.metadata_json = result.metadata

        region_states[result.region] = region_state
        status.region_states = region_states
        status.visible_regions = sorted(visible_regions)
        status.invisible_regions = sorted(invisible_regions)

        for event in events:
            session.add(event)
        return events

    def _has_metadata_change(self, status: AppStatusCurrent, result: StoreFetchResult) -> bool:
        if not status.last_title and not status.last_version:
            return False
        return any(
            [
                result.title and result.title != status.last_title,
                result.developer_name and result.developer_name != status.last_developer_name,
                result.category and result.category != status.last_category,
            ]
        )

    def _has_version_update(
        self,
        status: AppStatusCurrent,
        result: StoreFetchResult,
        watched_app: WatchedApp,
    ) -> bool:
        if not watched_app.notify_on_version_update:
            return False
        if result.fetch_status != "success" or not result.is_visible:
            return False
        if not status.last_version or not result.version:
            return False
        return result.version != status.last_version

    def _build_event(
        self,
        *,
        event_type: str,
        store: str,
        watched_app_id: str,
        region: str | None,
        payload: dict,
        dedupe_key: str,
    ) -> Event:
        return Event(
            event_type=event_type,
            store=store,
            watched_app_id=watched_app_id,
            region=region,
            payload=payload,
            dedupe_key=dedupe_key,
            status="pending",
            created_at=datetime.now(timezone.utc),
        )

    def _event_payload(
        self,
        watched_app: WatchedApp,
        result: StoreFetchResult,
        visible_regions: set[str],
        extra_payload: dict | None = None,
    ) -> dict:
        payload = {
            "display_name": watched_app.display_name or result.title,
            "package_name": watched_app.package_name,
            "bundle_id": watched_app.bundle_id,
            "app_id": watched_app.app_id,
            "title": result.title,
            "developer_name": result.developer_name,
            "version": result.version,
            "category": result.category,
            "url": result.url,
            "region": result.region,
            "visible_regions": sorted(visible_regions),
            "metadata": result.metadata,
        }
        if extra_payload:
            payload.update(extra_payload)
        return payload

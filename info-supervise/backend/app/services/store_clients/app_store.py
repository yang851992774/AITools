from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote_plus

import httpx

from app.core.config import get_settings
from app.schemas.common import PublisherAppRecord, PublisherDiscoveryResult, StoreEnum, StoreFetchResult


class AppStoreClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.timeout = self.settings.request_timeout_seconds

    async def fetch_app(
        self,
        *,
        region: str,
        bundle_id: str | None = None,
        app_id: str | None = None,
    ) -> StoreFetchResult:
        params: dict[str, Any] = {"country": region.upper()}
        if bundle_id:
            params["bundleId"] = bundle_id
        elif app_id:
            params["id"] = app_id
        else:
            raise ValueError("bundle_id or app_id is required for App Store monitoring")

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get("https://itunes.apple.com/lookup", params=params)
            response.raise_for_status()
            payload = response.json()

        results = payload.get("results", [])
        record = results[0] if results else None
        observed_at = datetime.now(timezone.utc)
        if not record:
            return StoreFetchResult(
                store=StoreEnum.APP_STORE,
                region=region.upper(),
                is_visible=False,
                url=self._build_app_url(region=region, bundle_id=bundle_id, app_id=app_id),
                raw_payload=payload,
                observed_at=observed_at,
            )

        icon_url = record.get("artworkUrl512") or record.get("artworkUrl100")

        return StoreFetchResult(
            store=StoreEnum.APP_STORE,
            region=region.upper(),
            is_visible=True,
            title=record.get("trackName"),
            developer_name=record.get("sellerName") or record.get("artistName"),
            version=record.get("version"),
            category=record.get("primaryGenreName"),
            url=record.get("trackViewUrl") or self._build_app_url(region=region, bundle_id=bundle_id, app_id=app_id),
            icon_url=icon_url,
            metadata={
                "track_id": record.get("trackId"),
                "bundle_id": record.get("bundleId"),
                "minimum_os_version": record.get("minimumOsVersion"),
                "genres": record.get("genres", []),
                "track_view_url": record.get("trackViewUrl"),
                "release_date": record.get("releaseDate"),
                "icon_url": icon_url,
            },
            raw_payload=record,
            observed_at=observed_at,
        )

    async def discover_publisher(
        self,
        *,
        region: str,
        publisher_name: str,
    ) -> PublisherDiscoveryResult:
        params = {
            "term": publisher_name,
            "country": region.upper(),
            "entity": "software",
            "limit": 200,
        }
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get("https://itunes.apple.com/search", params=params)
            response.raise_for_status()
            payload = response.json()

        apps: list[PublisherAppRecord] = []
        raw_payload: list[dict] = []
        publisher_norm = publisher_name.casefold()
        for record in payload.get("results", []):
            genre_name = (record.get("primaryGenreName") or "").strip()
            developer = record.get("sellerName") or record.get("artistName") or ""
            developer_norm = developer.casefold()
            if publisher_norm not in developer_norm:
                continue
            if "game" not in genre_name.casefold():
                continue
            track_id = str(record.get("trackId"))
            apps.append(
                PublisherAppRecord(
                    external_key=f"app_store:{track_id}",
                    name=record.get("trackName") or track_id,
                    developer_name=developer or None,
                    url=record.get("trackViewUrl"),
                    bundle_id=record.get("bundleId"),
                    app_id=track_id,
                    category=genre_name or None,
                    metadata={
                        "genres": record.get("genres", []),
                        "release_date": record.get("releaseDate"),
                    },
                )
            )
            raw_payload.append(record)

        return PublisherDiscoveryResult(
            store=StoreEnum.APP_STORE,
            region=region.upper(),
            apps=apps,
            raw_payload=raw_payload,
            observed_at=datetime.now(timezone.utc),
        )

    def _build_app_url(self, *, region: str, bundle_id: str | None, app_id: str | None) -> str:
        if app_id:
            return f"https://apps.apple.com/{region.lower()}/app/id{app_id}"
        if bundle_id:
            return f"https://itunes.apple.com/lookup?bundleId={quote_plus(bundle_id)}&country={region.upper()}"
        return f"https://apps.apple.com/{region.lower()}"

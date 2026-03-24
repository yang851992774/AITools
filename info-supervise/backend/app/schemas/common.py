from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class StoreEnum(str, Enum):
    GOOGLE_PLAY = "google_play"
    APP_STORE = "app_store"


class EventTypeEnum(str, Enum):
    APP_VISIBLE_FIRST_SEEN = "app_visible_first_seen"
    APP_VISIBLE_REGION_ADDED = "app_visible_region_added"
    APP_REMOVED_FROM_STORE = "app_removed_from_store"
    APP_REMOVED_FROM_REGION = "app_removed_from_region"
    APP_VERSION_UPDATED = "app_version_updated"
    PUBLISHER_NEW_GAME_DETECTED = "publisher_new_game_detected"
    METADATA_CHANGED_SIGNIFICANTLY = "metadata_changed_significantly"
    MONITOR_FAILED_REPEATEDLY = "monitor_failed_repeatedly"


class JobNameEnum(str, Enum):
    MONITOR_APPS = "monitor_apps"
    DISCOVER_PUBLISHERS = "discover_publishers"
    DELIVER_NOTIFICATIONS = "deliver_notifications"


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class StoreFetchResult(BaseModel):
    store: StoreEnum
    region: str
    is_visible: bool | None = None
    fetch_status: str = "success"
    title: str | None = None
    developer_name: str | None = None
    version: str | None = None
    category: str | None = None
    url: str | None = None
    icon_url: str | None = None
    metadata: dict = Field(default_factory=dict)
    raw_payload: dict = Field(default_factory=dict)
    observed_at: datetime


class PublisherAppRecord(BaseModel):
    external_key: str
    name: str
    developer_name: str | None = None
    url: str | None = None
    package_name: str | None = None
    bundle_id: str | None = None
    app_id: str | None = None
    category: str | None = None
    metadata: dict = Field(default_factory=dict)


class PublisherDiscoveryResult(BaseModel):
    store: StoreEnum
    region: str
    apps: list[PublisherAppRecord] = Field(default_factory=list)
    raw_payload: list[dict] = Field(default_factory=list)
    observed_at: datetime

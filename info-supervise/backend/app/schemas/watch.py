from __future__ import annotations

import math
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel, StoreEnum

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class AppStatusSummary(ORMModel):
    visible_regions: list[str] | None = None
    invisible_regions: list[str] | None = None
    last_seen_visible_at: datetime | None = None
    last_seen_invisible_at: datetime | None = None
    last_checked_at: datetime | None = None
    last_title: str | None = None
    last_developer_name: str | None = None
    last_version: str | None = None
    last_category: str | None = None
    last_url: str | None = None
    last_icon_url: str | None = None
    last_rating: float | None = None
    last_rating_count: int | None = None
    last_price: str | None = None
    last_release_notes: str | None = None
    last_file_size: str | None = None
    last_content_rating: str | None = None
    last_store_updated_at: str | None = None


class WatchedAppCreate(ORMModel):
    store: StoreEnum
    package_name: str | None = None
    bundle_id: str | None = None
    app_id: str | None = None
    display_name: str | None = None
    regions: list[str] = Field(default_factory=list)
    notify_on_version_update: bool = True
    check_interval_minutes: int = Field(default=30, ge=5, le=1440)
    tags: list[str] = Field(default_factory=list)

    @field_validator("regions")
    @classmethod
    def normalize_regions(cls, value: list[str]) -> list[str]:
        return [region.strip().upper() for region in value if region.strip()]

    @field_validator("app_id")
    @classmethod
    def normalize_app_id(cls, value: str | None) -> str | None:
        return value.strip() if value else value


class WatchedAppRead(ORMModel):
    id: str
    store: StoreEnum
    package_name: str | None = None
    bundle_id: str | None = None
    app_id: str | None = None
    display_name: str | None = None
    regions: list[str]
    monitoring_enabled: bool
    auto_added: bool
    notify_on_version_update: bool
    check_interval_minutes: int
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class WatchedAppWithStatus(WatchedAppRead):
    status: AppStatusSummary | None = None


class WatchedAppUpdate(ORMModel):
    display_name: str | None = None
    regions: list[str] | None = None
    monitoring_enabled: bool | None = None
    notify_on_version_update: bool | None = None
    check_interval_minutes: int | None = Field(default=None, ge=5, le=1440)
    tags: list[str] | None = None

    @field_validator("regions")
    @classmethod
    def normalize_regions(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        return [region.strip().upper() for region in value if region.strip()]


class WatchedPublisherCreate(ORMModel):
    store: StoreEnum
    publisher_name: str
    publisher_ref: str | None = None
    publisher_url: str | None = None
    regions: list[str] = Field(default_factory=list)
    auto_add_apps: bool = True
    auto_added_notify_on_version_update: bool = True

    @field_validator("regions")
    @classmethod
    def normalize_regions(cls, value: list[str]) -> list[str]:
        return [region.strip().upper() for region in value if region.strip()]


class WatchedPublisherRead(ORMModel):
    id: str
    store: StoreEnum
    publisher_name: str
    publisher_ref: str | None = None
    publisher_url: str | None = None
    regions: list[str]
    monitoring_enabled: bool
    auto_add_apps: bool
    auto_added_notify_on_version_update: bool
    created_at: datetime
    updated_at: datetime


class WatchedPublisherUpdate(ORMModel):
    publisher_name: str | None = None
    publisher_ref: str | None = None
    publisher_url: str | None = None
    regions: list[str] | None = None
    monitoring_enabled: bool | None = None
    auto_add_apps: bool | None = None
    auto_added_notify_on_version_update: bool | None = None

    @field_validator("regions")
    @classmethod
    def normalize_regions(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        return [region.strip().upper() for region in value if region.strip()]

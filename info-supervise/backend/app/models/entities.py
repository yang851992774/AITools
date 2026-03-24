from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class WatchedApp(Base):
    __tablename__ = "watched_apps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    store: Mapped[str] = mapped_column(String(32), index=True)
    package_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    bundle_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    app_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    regions: Mapped[list[str]] = mapped_column(JSON, default=list)
    monitoring_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_added: Mapped[bool] = mapped_column(Boolean, default=False)
    notify_on_version_update: Mapped[bool] = mapped_column(Boolean, default=True)
    check_interval_minutes: Mapped[int] = mapped_column(Integer, default=30)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class WatchedPublisher(Base):
    __tablename__ = "watched_publishers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    store: Mapped[str] = mapped_column(String(32), index=True)
    publisher_name: Mapped[str] = mapped_column(String(255), index=True)
    publisher_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    publisher_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    regions: Mapped[list[str]] = mapped_column(JSON, default=list)
    monitoring_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_add_apps: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_added_notify_on_version_update: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AppStoreSnapshot(Base):
    __tablename__ = "app_store_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    watched_app_id: Mapped[str] = mapped_column(ForeignKey("watched_apps.id", ondelete="CASCADE"), index=True)
    store: Mapped[str] = mapped_column(String(32), index=True)
    region: Mapped[str] = mapped_column(String(16), index=True)
    is_visible: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    fetch_status: Mapped[str] = mapped_column(String(32), default="success")
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    developer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class PublisherSnapshot(Base):
    __tablename__ = "publisher_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    watched_publisher_id: Mapped[str] = mapped_column(
        ForeignKey("watched_publishers.id", ondelete="CASCADE"),
        index=True,
    )
    store: Mapped[str] = mapped_column(String(32), index=True)
    region: Mapped[str] = mapped_column(String(16), index=True)
    app_keys: Mapped[list[str]] = mapped_column(JSON, default=list)
    raw_payload: Mapped[list[dict]] = mapped_column(JSON, default=list)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class AppStatusCurrent(Base):
    __tablename__ = "app_status_current"
    __table_args__ = (UniqueConstraint("watched_app_id", name="uq_app_status_current_watched_app_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    watched_app_id: Mapped[str] = mapped_column(ForeignKey("watched_apps.id", ondelete="CASCADE"), index=True)
    store: Mapped[str] = mapped_column(String(32), index=True)
    visible_regions: Mapped[list[str]] = mapped_column(JSON, default=list)
    invisible_regions: Mapped[list[str]] = mapped_column(JSON, default=list)
    region_states: Mapped[dict] = mapped_column(JSON, default=dict)
    last_seen_visible_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_invisible_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_developer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    store: Mapped[str] = mapped_column(String(32), index=True)
    watched_app_id: Mapped[str | None] = mapped_column(ForeignKey("watched_apps.id", ondelete="SET NULL"), nullable=True)
    watched_publisher_id: Mapped[str | None] = mapped_column(
        ForeignKey("watched_publishers.id", ondelete="SET NULL"),
        nullable=True,
    )
    region: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    dedupe_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class NotificationChannel(Base):
    __tablename__ = "notification_channels"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    channel_type: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    webhook_url: Mapped[str] = mapped_column(String(1000))
    secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class JobRun(Base):
    __tablename__ = "job_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    job_name: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detail_json: Mapped[dict] = mapped_column(JSON, default=dict)
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)

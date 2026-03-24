from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.common import EventTypeEnum, JobNameEnum, ORMModel, StoreEnum


class EventRead(ORMModel):
    id: str
    event_type: EventTypeEnum
    store: StoreEnum
    watched_app_id: str | None = None
    watched_publisher_id: str | None = None
    region: str | None = None
    dedupe_key: str | None = None
    payload: dict = Field(default_factory=dict)
    status: str
    sent_at: datetime | None = None
    last_error: str | None = None
    created_at: datetime


class JobRunRequest(ORMModel):
    job_name: JobNameEnum


class JobRunResponse(ORMModel):
    job_name: str
    status: str
    detail: dict = Field(default_factory=dict)


class JobRunRead(ORMModel):
    id: str
    job_name: str
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    duration_ms: int | None = None
    detail_json: dict = Field(default_factory=dict)
    error_text: str | None = None

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.events import EventRead
from app.schemas.watch import PaginatedResponse
from app.services.monitoring import MonitoringService

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[EventRead])
async def list_events(
    limit: int = Query(default=100, ge=1, le=500),
    status: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    store: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[EventRead]:
    service = MonitoringService(db)
    events = await service.list_filtered_events(
        limit=limit,
        status=status,
        event_type=event_type,
        store=store,
    )
    return [EventRead.model_validate(event) for event in events]


@router.get("/paged")
async def list_events_paged(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    store: str | None = Query(default=None),
    q: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse:
    service = MonitoringService(db)
    return await service.list_events_paged(
        page=page,
        page_size=page_size,
        status=status,
        event_type=event_type,
        store=store,
        q=q,
    )

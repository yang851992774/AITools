from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.watch import PaginatedResponse, WatchedPublisherCreate, WatchedPublisherRead, WatchedPublisherUpdate
from app.services.monitoring import MonitoringService

router = APIRouter(prefix="/watch/publishers", tags=["watch-publishers"])


@router.post("", response_model=WatchedPublisherRead, status_code=status.HTTP_201_CREATED)
async def create_watched_publisher(
    payload: WatchedPublisherCreate,
    db: AsyncSession = Depends(get_db),
) -> WatchedPublisherRead:
    service = MonitoringService(db)
    publisher = await service.create_watched_publisher(payload)
    return WatchedPublisherRead.model_validate(publisher)


@router.get("", response_model=PaginatedResponse[WatchedPublisherRead])
async def list_watched_publishers(
    page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数，最大 100"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[WatchedPublisherRead]:
    service = MonitoringService(db)
    return await service.list_watched_publishers_paged(page=page, page_size=page_size)


@router.patch("/{publisher_id}", response_model=WatchedPublisherRead)
async def update_watched_publisher(
    publisher_id: str,
    payload: WatchedPublisherUpdate,
    db: AsyncSession = Depends(get_db),
) -> WatchedPublisherRead:
    service = MonitoringService(db)
    try:
        publisher = await service.update_watched_publisher(publisher_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return WatchedPublisherRead.model_validate(publisher)


@router.delete("/{publisher_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watched_publisher(
    publisher_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    service = MonitoringService(db)
    try:
        await service.delete_watched_publisher(publisher_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.watch import PaginatedResponse, WatchedAppCreate, WatchedAppRead, WatchedAppUpdate, WatchedAppWithStatus
from app.services.monitoring import MonitoringService

router = APIRouter(prefix="/watch/apps", tags=["watch-apps"])


@router.post("", response_model=WatchedAppRead, status_code=status.HTTP_201_CREATED)
async def create_watched_app(
    payload: WatchedAppCreate,
    db: AsyncSession = Depends(get_db),
) -> WatchedAppRead:
    service = MonitoringService(db)
    try:
        watched_app = await service.create_watched_app(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return WatchedAppRead.model_validate(watched_app)


@router.get("", response_model=PaginatedResponse[WatchedAppWithStatus])
async def list_watched_apps(
    page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数，最大 100"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[WatchedAppWithStatus]:
    service = MonitoringService(db)
    return await service.list_watched_apps_paged(page=page, page_size=page_size)


@router.patch("/{app_id}", response_model=WatchedAppRead)
async def update_watched_app(
    app_id: str,
    payload: WatchedAppUpdate,
    db: AsyncSession = Depends(get_db),
) -> WatchedAppRead:
    service = MonitoringService(db)
    try:
        watched_app = await service.update_watched_app(app_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return WatchedAppRead.model_validate(watched_app)


@router.delete("/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watched_app(
    app_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    service = MonitoringService(db)
    try:
        await service.delete_watched_app(app_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
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
    store: str | None = Query(default=None, description="按商店过滤: google_play / app_store"),
    q: str | None = Query(default=None, description="模糊搜索：应用名/包名/bundle_id"),
    tag: str | None = Query(default=None, description="按标签过滤"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[WatchedAppWithStatus]:
    service = MonitoringService(db)
    return await service.list_watched_apps_paged(page=page, page_size=page_size, store=store, q=q, tag=tag)


@router.get("/export")
async def export_watched_apps(
    store: str | None = Query(default=None),
    q: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    service = MonitoringService(db)
    data = await service.list_watched_apps_paged(page=1, page_size=10000, store=store, q=q, tag=tag)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "应用名", "商店", "包名/BundleID", "当前版本", "评分", "评分人数",
        "价格", "区域", "标签", "最近检查", "可见区域",
    ])
    for item in data.items:
        s = item.status
        writer.writerow([
            item.display_name or item.package_name or item.bundle_id or item.app_id,
            item.store.value if hasattr(item.store, "value") else item.store,
            item.package_name or item.bundle_id or item.app_id or "",
            s.last_version if s else "",
            s.last_rating if s else "",
            s.last_rating_count if s else "",
            s.last_price if s else "",
            ", ".join(item.regions),
            ", ".join(item.tags) if item.tags else "",
            s.last_checked_at.isoformat() if s and s.last_checked_at else "",
            ", ".join(s.visible_regions) if s and s.visible_regions else "",
        ])
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=apps_export.csv"},
    )


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

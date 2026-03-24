from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.monitoring import MonitoringService
from app.services.store_clients.http_client import get_global_stats

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)) -> dict:
    service = MonitoringService(db)
    return await service.get_dashboard_summary()


@router.get("/fetch-stats")
async def get_fetch_stats() -> dict:
    return get_global_stats().to_dict()

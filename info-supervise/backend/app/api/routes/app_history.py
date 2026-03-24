from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.entities import AppStoreSnapshot

router = APIRouter(prefix="/watch/apps", tags=["watch-apps"])


@router.get("/{app_id}/history")
async def get_app_history(
    app_id: str,
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    snapshots = await db.scalars(
        select(AppStoreSnapshot)
        .where(
            AppStoreSnapshot.watched_app_id == app_id,
            AppStoreSnapshot.observed_at >= cutoff,
        )
        .order_by(AppStoreSnapshot.observed_at.asc())
    )
    return [
        {
            "id": s.id,
            "region": s.region,
            "is_visible": s.is_visible,
            "title": s.title,
            "version": s.version,
            "category": s.category,
            "metadata_json": s.metadata_json,
            "observed_at": s.observed_at.isoformat(),
        }
        for s in snapshots.all()
    ]

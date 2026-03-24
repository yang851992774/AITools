from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.events import JobRunRead, JobRunRequest, JobRunResponse
from app.services.monitoring import MonitoringService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/run", response_model=JobRunResponse)
async def run_job(
    payload: JobRunRequest,
    db: AsyncSession = Depends(get_db),
) -> JobRunResponse:
    service = MonitoringService(db)
    return await service.execute_job(payload.job_name)


@router.get("/runs", response_model=list[JobRunRead])
async def list_job_runs(db: AsyncSession = Depends(get_db)) -> list[JobRunRead]:
    service = MonitoringService(db)
    runs = await service.list_job_runs()
    return [JobRunRead.model_validate(item) for item in runs]

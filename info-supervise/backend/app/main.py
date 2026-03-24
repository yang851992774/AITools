from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.routes import dashboard, events, jobs, watch_apps, watch_publishers
from app.core.redis_client import get_redis
from app.db.session import AsyncSessionLocal
from app.db.session import engine
from app.services.monitoring import MonitoringService

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with AsyncSessionLocal() as session:
        service = MonitoringService(session)
        await service.ensure_default_notification_channel()
    yield


app = FastAPI(
    title="Info Supervise",
    description="Game store monitoring service for Google Play and App Store",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(watch_apps.router)
app.include_router(watch_publishers.router)
app.include_router(events.router)
app.include_router(jobs.router)
app.include_router(dashboard.router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health", tags=["health"])
async def health() -> dict:
    db_ok = False
    redis_ok = False

    async with engine.begin() as connection:
        await connection.execute(text("SELECT 1"))
        db_ok = True

    redis = get_redis()
    redis_ok = (await redis.ping()) is True

    return {
        "status": "ok" if db_ok and redis_ok else "degraded",
        "database": db_ok,
        "redis": redis_ok,
    }

from __future__ import annotations

from contextlib import asynccontextmanager
from functools import lru_cache
from uuid import uuid4

from redis.asyncio import Redis, from_url

from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_redis() -> Redis:
    settings = get_settings()
    return from_url(settings.redis_url, decode_responses=True)


@asynccontextmanager
async def redis_job_lock(lock_name: str, ttl_seconds: int):
    redis = get_redis()
    token = str(uuid4())
    acquired = await redis.set(lock_name, token, ex=ttl_seconds, nx=True)
    try:
        yield bool(acquired)
    finally:
        if acquired:
            current = await redis.get(lock_name)
            if current == token:
                await redis.delete(lock_name)

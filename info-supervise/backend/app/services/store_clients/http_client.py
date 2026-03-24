"""Shared rate-limited HTTP client with jitter, retry, backoff, UA rotation, and optional proxy."""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass, field
from time import monotonic

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class FetchStats:
    """Mutable counters collected during a single job run."""

    requests: int = 0
    successes: int = 0
    retries: int = 0
    rate_limited: int = 0
    forbidden: int = 0
    errors: int = 0
    cooldowns_triggered: int = 0
    total_latency_ms: float = 0.0

    def to_dict(self) -> dict:
        avg = round(self.total_latency_ms / self.requests, 1) if self.requests else 0
        return {
            "requests": self.requests,
            "successes": self.successes,
            "retries": self.retries,
            "rate_limited": self.rate_limited,
            "forbidden": self.forbidden,
            "errors": self.errors,
            "cooldowns_triggered": self.cooldowns_triggered,
            "avg_latency_ms": avg,
        }


@dataclass
class StoreStats:
    """Per-store statistics keyed by store name."""

    stores: dict[str, FetchStats] = field(default_factory=dict)

    def get(self, store: str) -> FetchStats:
        if store not in self.stores:
            self.stores[store] = FetchStats()
        return self.stores[store]

    def to_dict(self) -> dict:
        return {k: v.to_dict() for k, v in self.stores.items()}


_global_stats = StoreStats()


def get_global_stats() -> StoreStats:
    return _global_stats


def reset_global_stats() -> StoreStats:
    global _global_stats
    _global_stats = StoreStats()
    return _global_stats


_cooldown_until: dict[str, float] = {}


def _is_in_cooldown(store: str) -> bool:
    deadline = _cooldown_until.get(store, 0)
    return monotonic() < deadline


def _enter_cooldown(store: str) -> None:
    settings = get_settings()
    _cooldown_until[store] = monotonic() + settings.store_cooldown_minutes * 60
    _global_stats.get(store).cooldowns_triggered += 1
    logger.warning("Store %s entering cooldown for %d minutes", store, settings.store_cooldown_minutes)


def _pick_ua() -> str:
    settings = get_settings()
    pool = settings.ua_pool_list
    return random.choice(pool)


def _pick_proxy() -> str | None:
    settings = get_settings()
    proxies = settings.proxy_url_list
    if not proxies:
        return None
    return random.choice(proxies)


async def _jitter_delay() -> None:
    settings = get_settings()
    base = settings.store_request_min_delay_ms
    jitter = settings.store_request_jitter_ms
    delay_ms = base + random.randint(0, jitter)
    await asyncio.sleep(delay_ms / 1000.0)


async def resilient_get(
    url: str,
    *,
    store: str,
    params: dict | None = None,
    extra_headers: dict | None = None,
    timeout: int | None = None,
) -> httpx.Response:
    """HTTP GET with jitter, retry, exponential backoff, UA rotation, and cooldown."""
    settings = get_settings()
    max_retries = settings.store_max_retries
    backoff_ms = settings.store_retry_backoff_ms
    stats = _global_stats.get(store)
    timeout = timeout or settings.request_timeout_seconds

    if _is_in_cooldown(store):
        logger.info("Store %s is in cooldown, returning synthetic 429", store)
        stats.rate_limited += 1
        stats.requests += 1
        resp = httpx.Response(status_code=429, text="cooldown active")
        return resp

    await _jitter_delay()

    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        stats.requests += 1
        if attempt > 0:
            stats.retries += 1

        headers = {"User-Agent": _pick_ua(), "Accept-Language": "en-US,en;q=0.9"}
        if extra_headers:
            headers.update(extra_headers)

        proxy_url = _pick_proxy()
        t0 = monotonic()
        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                headers=headers,
                follow_redirects=True,
                proxy=proxy_url,
            ) as client:
                response = await client.get(url, params=params)

            elapsed = (monotonic() - t0) * 1000
            stats.total_latency_ms += elapsed

            if response.status_code == 429:
                stats.rate_limited += 1
                logger.warning("429 from %s (attempt %d/%d)", store, attempt + 1, max_retries + 1)
                if attempt == max_retries:
                    _enter_cooldown(store)
                    return response
                await asyncio.sleep(backoff_ms * (2 ** attempt) / 1000.0)
                continue

            if response.status_code == 403:
                stats.forbidden += 1
                logger.warning("403 from %s (attempt %d/%d)", store, attempt + 1, max_retries + 1)
                if attempt == max_retries:
                    _enter_cooldown(store)
                    return response
                await asyncio.sleep(backoff_ms * (2 ** attempt) / 1000.0)
                continue

            stats.successes += 1
            return response

        except Exception as exc:  # noqa: BLE001
            elapsed = (monotonic() - t0) * 1000
            stats.total_latency_ms += elapsed
            stats.errors += 1
            last_exc = exc
            logger.warning("Request error from %s: %s (attempt %d/%d)", store, exc, attempt + 1, max_retries + 1)
            if attempt < max_retries:
                await asyncio.sleep(backoff_ms * (2 ** attempt) / 1000.0)

    raise last_exc or RuntimeError(f"All {max_retries + 1} attempts exhausted for {store}")

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://info_supervise:info_supervise@localhost:5432/info_supervise"
    redis_url: str = "redis://localhost:6379/0"

    default_regions: str = Field(default="US,JP,KR,TW,HK", alias="DEFAULT_REGIONS")
    visibility_confirm_threshold: int = 2
    app_monitor_interval_minutes: int = 30
    publisher_monitor_interval_hours: int = 4
    notification_interval_minutes: int = 2
    request_timeout_seconds: int = 20
    enable_browser_fallback: bool = False
    event_dedupe_window_minutes: int = 30
    job_lock_ttl_seconds: int = 1800
    user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    )

    feishu_webhook_url: str | None = None
    feishu_secret: str | None = None

    @property
    def normalized_regions(self) -> list[str]:
        return [region.strip().upper() for region in self.default_regions.split(",") if region.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

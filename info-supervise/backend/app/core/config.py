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

    store_request_min_delay_ms: int = 800
    store_request_jitter_ms: int = 1200
    store_max_retries: int = 3
    store_retry_backoff_ms: int = 2000
    store_cooldown_minutes: int = 15
    store_adaptive_no_change_threshold: int = 5
    store_adaptive_max_interval_multiplier: int = 4
    store_proxy_urls: str = ""
    store_ua_pool: str = ""
    store_alert_rate_limit_pct: int = 15
    store_alert_error_pct: int = 20
    store_alert_min_requests: int = 5

    feishu_webhook_url: str | None = None
    feishu_secret: str | None = None

    digest_enabled: bool = False
    digest_hour: int = 10

    @property
    def normalized_regions(self) -> list[str]:
        return [region.strip().upper() for region in self.default_regions.split(",") if region.strip()]

    @property
    def proxy_url_list(self) -> list[str]:
        return [u.strip() for u in self.store_proxy_urls.split(",") if u.strip()]

    @property
    def ua_pool_list(self) -> list[str]:
        defaults = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
        ]
        custom = [u.strip() for u in self.store_ua_pool.split("|") if u.strip()]
        return custom if custom else defaults


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

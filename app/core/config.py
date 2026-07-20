from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False
    api_host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    forwarded_allow_ips: str = "*"
    auto_create_schema: bool = True
    pocketoption_base_url: str = "https://pocketoptionapi-mainscalp-production-0434.up.railway.app"
    allow_live_trading: bool = False
    default_account_mode: Literal["demo", "real"] = "demo"
    engine_mode: Literal["signal_only", "demo_auto", "live_auto"] = "signal_only"
    default_asset: str = "EURUSD_otc"
    default_timeframe_seconds: int = 5
    default_expiration_seconds: int = 30
    default_order_amount: float = 1
    max_order_amount: float = 10
    max_daily_loss: float = 20
    max_consecutive_losses: int = 3
    max_orders_per_hour: int = 10
    min_signal_score: int = 16
    min_direction_score_difference: int = 4
    order_cooldown_seconds: int = 30
    loss_cooldown_seconds: int = 120
    min_payout: float = 0
    market_poll_interval_ms: int = 500
    engine_loop_interval_ms: int = 500
    http_timeout_seconds: float = 15
    max_external_latency_ms: int = 5000
    log_level: str = "INFO"
    database_url: str = "sqlite+aiosqlite:///./trading_engine.db"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    trusted_hosts: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1", "testserver", "healthcheck.railway.app", "*.up.railway.app"])
    max_body_bytes: int = 64 * 1024
    sensitive_rate_limit: int = 20
    sensitive_rate_window_seconds: int = 60

    @property
    def normalized_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgres://"):
            url = "postgresql+asyncpg://" + url.removeprefix("postgres://")
        elif url.startswith("postgresql://"):
            url = "postgresql+asyncpg://" + url.removeprefix("postgresql://")
        return url.replace("sslmode=", "ssl=")

@lru_cache
def get_settings() -> Settings:
    return Settings()

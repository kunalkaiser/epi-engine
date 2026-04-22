from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os


@dataclass(frozen=True)
class Settings:
    app_env: str
    log_level: str
    api_host: str
    api_port: int
    cors_origins: tuple[str, ...]
    clickhouse_url: str
    clickhouse_database: str
    clickhouse_user: str
    clickhouse_password: str
    clickhouse_timeout_seconds: int
    db_fallback_enabled: bool
    auth_jwt_secret: str
    auth_jwt_issuer: str
    auth_jwt_audience: str


def get_settings() -> Settings:
    return _get_settings()


@lru_cache(maxsize=1)
def _get_settings() -> Settings:
    raw_origins = os.getenv("API_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    origins = tuple(origin.strip() for origin in raw_origins.split(",") if origin.strip())
    return Settings(
        app_env=os.getenv("APP_ENV", "development"),
        log_level=os.getenv("API_LOG_LEVEL", "INFO").upper(),
        api_host=os.getenv("API_HOST", "0.0.0.0"),
        api_port=int(os.getenv("API_PORT", "8000")),
        cors_origins=origins,
        clickhouse_url=os.getenv("CLICKHOUSE_URL", "http://localhost:8123"),
        clickhouse_database=os.getenv("CLICKHOUSE_DATABASE", "epi_engine"),
        clickhouse_user=os.getenv("CLICKHOUSE_USER", "default"),
        clickhouse_password=os.getenv("CLICKHOUSE_PASSWORD", ""),
        clickhouse_timeout_seconds=int(os.getenv("CLICKHOUSE_TIMEOUT_SECONDS", "5")),
        db_fallback_enabled=os.getenv("DB_FALLBACK_ENABLED", "true").lower() == "true",
        auth_jwt_secret=os.getenv("AUTH_JWT_SECRET", ""),
        auth_jwt_issuer=os.getenv("AUTH_JWT_ISSUER", "epi-engine"),
        auth_jwt_audience=os.getenv("AUTH_JWT_AUDIENCE", "epi-engine-clients"),
    )


def clear_settings_cache() -> None:
    _get_settings.cache_clear()

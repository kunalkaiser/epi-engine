from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os


VALID_APP_ENVS = {"development", "test", "staging", "production"}
INSECURE_DEFAULT_SECRETS = {"", "dev-secret", "changeme", "replace-with-strong-secret"}


@dataclass(frozen=True)
class Settings:
    app_env: str
    log_level: str
    api_host: str
    api_port: int
    cors_origins: tuple[str, ...]
    db_backend: str
    clickhouse_url: str
    clickhouse_database: str
    clickhouse_user: str
    clickhouse_password: str
    clickhouse_timeout_seconds: int
    database_url: str
    pg_schema: str
    pg_timeout_seconds: int
    db_fallback_enabled: bool
    auth_jwt_secret: str
    auth_jwt_issuer: str
    auth_jwt_audience: str
    require_tenant_claim_non_dev: bool
    metrics_enabled: bool
    trace_header_name: str
    pilot_mode_enabled: bool
    pilot_mode_label: str
    evidence_os_url: str


def get_settings() -> Settings:
    return _get_settings()


@lru_cache(maxsize=1)
def _get_settings() -> Settings:
    raw_origins = os.getenv("API_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    origins = tuple(origin.strip() for origin in raw_origins.split(",") if origin.strip())
    settings = Settings(
        app_env=os.getenv("APP_ENV", "development"),
        log_level=os.getenv("API_LOG_LEVEL", "INFO").upper(),
        api_host=os.getenv("API_HOST", "0.0.0.0"),
        api_port=int(os.getenv("API_PORT", "8000")),
        cors_origins=origins,
        db_backend=os.getenv("DB_BACKEND", "clickhouse").lower(),
        clickhouse_url=os.getenv("CLICKHOUSE_URL", "http://localhost:8123"),
        clickhouse_database=os.getenv("CLICKHOUSE_DATABASE", "epi_engine"),
        clickhouse_user=os.getenv("CLICKHOUSE_USER", "default"),
        clickhouse_password=os.getenv("CLICKHOUSE_PASSWORD", ""),
        clickhouse_timeout_seconds=int(os.getenv("CLICKHOUSE_TIMEOUT_SECONDS", "30")),
        database_url=os.getenv("DATABASE_URL", ""),
        pg_schema=os.getenv("PG_SCHEMA", "epi_engine"),
        pg_timeout_seconds=int(os.getenv("PG_TIMEOUT_SECONDS", "10")),
        db_fallback_enabled=os.getenv("DB_FALLBACK_ENABLED", "true").lower() == "true",
        auth_jwt_secret=os.getenv("AUTH_JWT_SECRET", ""),
        auth_jwt_issuer=os.getenv("AUTH_JWT_ISSUER", "epi-engine"),
        auth_jwt_audience=os.getenv("AUTH_JWT_AUDIENCE", "epi-engine-clients"),
        require_tenant_claim_non_dev=os.getenv("REQUIRE_TENANT_CLAIM_NON_DEV", "true").lower() == "true",
        metrics_enabled=os.getenv("API_METRICS_ENABLED", "true").lower() == "true",
        trace_header_name=os.getenv("TRACE_HEADER_NAME", "X-Request-ID"),
        pilot_mode_enabled=os.getenv("PILOT_MODE_ENABLED", "false").lower() == "true",
        pilot_mode_label=os.getenv("PILOT_MODE_LABEL", "off"),
        evidence_os_url=os.getenv("EVIDENCE_OS_URL", "https://evidence-os-production.up.railway.app"),
    )
    _validate_settings(settings)
    return settings


def clear_settings_cache() -> None:
    _get_settings.cache_clear()


def _validate_settings(settings: Settings) -> None:
    if settings.app_env not in VALID_APP_ENVS:
        raise ValueError(f"APP_ENV must be one of {sorted(VALID_APP_ENVS)}")
    if settings.trace_header_name.strip() == "":
        raise ValueError("TRACE_HEADER_NAME must not be empty")
    if settings.pilot_mode_label.strip() == "":
        raise ValueError("PILOT_MODE_LABEL must not be empty")
    if not settings.cors_origins:
        raise ValueError("API_CORS_ORIGINS must include at least one origin")
    if settings.db_backend not in {"clickhouse", "postgres"}:
        raise ValueError("DB_BACKEND must be 'clickhouse' or 'postgres'")

    non_dev = settings.app_env in {"staging", "production"}
    if not non_dev:
        return

    if settings.db_fallback_enabled:
        raise ValueError("DB_FALLBACK_ENABLED must be false in staging/production")
    if settings.auth_jwt_secret in INSECURE_DEFAULT_SECRETS:
        raise ValueError("AUTH_JWT_SECRET must be set to a strong value in staging/production")
    if settings.db_backend == "postgres":
        if settings.database_url.strip() == "":
            raise ValueError("DATABASE_URL must be set when DB_BACKEND=postgres in staging/production")
        if "localhost" in settings.database_url or "127.0.0.1" in settings.database_url:
            raise ValueError("DATABASE_URL must not point to localhost in staging/production")
    else:
        if settings.clickhouse_password.strip() == "":
            raise ValueError("CLICKHOUSE_PASSWORD must be set in staging/production")
        if "localhost" in settings.clickhouse_url or "127.0.0.1" in settings.clickhouse_url:
            raise ValueError("CLICKHOUSE_URL must not point to localhost in staging/production")
    if any("localhost" in origin or "127.0.0.1" in origin for origin in settings.cors_origins):
        raise ValueError("API_CORS_ORIGINS must not contain localhost in staging/production")

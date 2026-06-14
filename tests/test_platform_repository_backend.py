from __future__ import annotations

from apps.api.platform_repository import PlatformPersistenceRepository, build_platform_repository
from apps.api.platform_repository_pg import PostgresPlatformRepository
from apps.api.settings import clear_settings_cache


def setup_function() -> None:
    clear_settings_cache()


def _ok_probe(self, sql, parameters=None):
    return [{"ok": 1}]


def test_build_platform_repository_uses_postgres_when_db_backend_postgres(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DB_FALLBACK_ENABLED", "false")
    monkeypatch.setenv("AUTH_JWT_SECRET", "prod-secret")
    monkeypatch.setenv("API_CORS_ORIGINS", "https://epios.example.com")
    monkeypatch.setenv("DB_BACKEND", "postgres")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db.example.com:6543/postgres")
    clear_settings_cache()
    monkeypatch.setattr("apps.api.pg.PostgresClient.query_json", _ok_probe)

    repository = build_platform_repository()

    assert isinstance(repository, PostgresPlatformRepository)


def test_build_platform_repository_uses_clickhouse_by_default(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DB_FALLBACK_ENABLED", "false")
    monkeypatch.setenv("AUTH_JWT_SECRET", "prod-secret")
    monkeypatch.setenv("API_CORS_ORIGINS", "https://epios.example.com")
    monkeypatch.setenv("DB_BACKEND", "clickhouse")
    monkeypatch.setenv("CLICKHOUSE_PASSWORD", "prod-password")
    monkeypatch.setenv("CLICKHOUSE_URL", "http://clickhouse:8123")
    clear_settings_cache()
    monkeypatch.setattr("apps.api.db.ClickHouseClient.query_json", _ok_probe)

    repository = build_platform_repository()

    assert isinstance(repository, PlatformPersistenceRepository)
    assert not isinstance(repository, PostgresPlatformRepository)

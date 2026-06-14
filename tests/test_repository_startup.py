from __future__ import annotations

import pytest

from apps.api.data import INDICATION_PROFILES
from apps.api.db import ClickHouseUnavailableError
from apps.api.repository import ClickHouseAnalyticsRepository, SyntheticAnalyticsRepository, build_analytics_repository
from apps.api.settings import clear_settings_cache


def setup_function() -> None:
    clear_settings_cache()


def test_build_repository_uses_clickhouse_in_non_development(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DB_FALLBACK_ENABLED", "false")
    monkeypatch.setenv("AUTH_JWT_SECRET", "prod-secret")
    monkeypatch.setenv("CLICKHOUSE_USER", "epi_engine_app")
    monkeypatch.setenv("CLICKHOUSE_PASSWORD", "prod-password")
    monkeypatch.setenv("CLICKHOUSE_URL", "http://clickhouse:8123")
    monkeypatch.setenv("API_CORS_ORIGINS", "https://epios.example.com")
    clear_settings_cache()

    repository = build_analytics_repository()

    assert isinstance(repository, ClickHouseAnalyticsRepository)


def test_build_repository_falls_back_in_development_when_clickhouse_unavailable(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DB_FALLBACK_ENABLED", "true")
    clear_settings_cache()

    def failing_probe(self, sql: str, parameters=None):
        raise ClickHouseUnavailableError("no clickhouse")

    monkeypatch.setattr("apps.api.db.ClickHouseClient.query_json", failing_probe)
    repository = build_analytics_repository()

    assert isinstance(repository, SyntheticAnalyticsRepository)


def test_build_repository_raises_in_development_when_fallback_disabled(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DB_FALLBACK_ENABLED", "false")
    clear_settings_cache()

    def failing_probe(self, sql: str, parameters=None):
        raise ClickHouseUnavailableError("no clickhouse")

    monkeypatch.setattr("apps.api.db.ClickHouseClient.query_json", failing_probe)

    with pytest.raises(ClickHouseUnavailableError):
        build_analytics_repository()


def test_build_repository_seeds_indication_profiles_when_clickhouse_table_is_empty(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DB_FALLBACK_ENABLED", "true")
    clear_settings_cache()

    calls: list[tuple[str, dict | None]] = []

    def fake_query(self, sql: str, parameters=None):
        calls.append((sql, parameters))
        if "SELECT 1 AS ok" in sql:
            return [{"ok": 1}]
        if "SELECT count(*) AS total_items FROM indication_profile_facts" in sql:
            return [{"total_items": 0}]
        if "INSERT INTO indication_profile_facts" in sql:
            return []
        raise AssertionError(f"unexpected SQL: {sql}")

    monkeypatch.setattr("apps.api.db.ClickHouseClient.query_json", fake_query)
    repository = build_analytics_repository()

    assert isinstance(repository, ClickHouseAnalyticsRepository)
    insert_calls = [sql for sql, _ in calls if "INSERT INTO indication_profile_facts" in sql]
    assert len(insert_calls) == len(INDICATION_PROFILES)


def test_build_repository_skips_seed_when_indication_profiles_exist(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DB_FALLBACK_ENABLED", "true")
    clear_settings_cache()

    calls: list[tuple[str, dict | None]] = []

    def fake_query(self, sql: str, parameters=None):
        calls.append((sql, parameters))
        if "SELECT 1 AS ok" in sql:
            return [{"ok": 1}]
        if "SELECT count(*) AS total_items FROM indication_profile_facts" in sql:
            return [{"total_items": 3}]
        if "INSERT INTO indication_profile_facts" in sql:
            raise AssertionError("seed insert should not run when rows already exist")
        return []

    monkeypatch.setattr("apps.api.db.ClickHouseClient.query_json", fake_query)
    repository = build_analytics_repository()

    assert isinstance(repository, ClickHouseAnalyticsRepository)

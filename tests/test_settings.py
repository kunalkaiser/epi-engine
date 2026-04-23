from apps.api.settings import clear_settings_cache, get_settings


def setup_function() -> None:
    clear_settings_cache()


def test_settings_use_defaults(monkeypatch) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("API_LOG_LEVEL", raising=False)
    monkeypatch.delenv("API_HOST", raising=False)
    monkeypatch.delenv("API_PORT", raising=False)
    monkeypatch.delenv("API_CORS_ORIGINS", raising=False)
    monkeypatch.delenv("AUTH_JWT_SECRET", raising=False)
    monkeypatch.delenv("AUTH_JWT_ISSUER", raising=False)
    monkeypatch.delenv("AUTH_JWT_AUDIENCE", raising=False)
    monkeypatch.delenv("REQUIRE_TENANT_CLAIM_NON_DEV", raising=False)

    settings = get_settings()

    assert settings.app_env == "development"
    assert settings.log_level == "INFO"
    assert settings.api_host == "0.0.0.0"
    assert settings.api_port == 8000
    assert settings.cors_origins == ("http://localhost:3000", "http://127.0.0.1:3000")
    assert settings.clickhouse_url == "http://localhost:8123"
    assert settings.clickhouse_database == "epi_engine"
    assert settings.clickhouse_user == "default"
    assert settings.clickhouse_password == ""
    assert settings.clickhouse_timeout_seconds == 5
    assert settings.db_fallback_enabled is True
    assert settings.auth_jwt_secret == ""
    assert settings.auth_jwt_issuer == "epi-engine"
    assert settings.auth_jwt_audience == "epi-engine-clients"
    assert settings.require_tenant_claim_non_dev is True
    assert settings.metrics_enabled is True
    assert settings.trace_header_name == "X-Request-ID"
    assert settings.pilot_mode_enabled is False
    assert settings.pilot_mode_label == "off"


def test_settings_parse_env(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("API_LOG_LEVEL", "debug")
    monkeypatch.setenv("API_HOST", "127.0.0.1")
    monkeypatch.setenv("API_PORT", "9001")
    monkeypatch.setenv("API_CORS_ORIGINS", "https://a.example, https://b.example")
    monkeypatch.setenv("CLICKHOUSE_URL", "http://clickhouse:8123")
    monkeypatch.setenv("CLICKHOUSE_DATABASE", "analytics")
    monkeypatch.setenv("CLICKHOUSE_USER", "epi")
    monkeypatch.setenv("CLICKHOUSE_PASSWORD", "secret")
    monkeypatch.setenv("CLICKHOUSE_TIMEOUT_SECONDS", "12")
    monkeypatch.setenv("DB_FALLBACK_ENABLED", "false")
    monkeypatch.setenv("AUTH_JWT_SECRET", "jwt-secret")
    monkeypatch.setenv("AUTH_JWT_ISSUER", "issuer")
    monkeypatch.setenv("AUTH_JWT_AUDIENCE", "audience")
    monkeypatch.setenv("REQUIRE_TENANT_CLAIM_NON_DEV", "false")
    clear_settings_cache()

    settings = get_settings()

    assert settings.app_env == "production"
    assert settings.log_level == "DEBUG"
    assert settings.api_host == "127.0.0.1"
    assert settings.api_port == 9001
    assert settings.cors_origins == ("https://a.example", "https://b.example")
    assert settings.clickhouse_url == "http://clickhouse:8123"
    assert settings.clickhouse_database == "analytics"
    assert settings.clickhouse_user == "epi"
    assert settings.clickhouse_password == "secret"
    assert settings.clickhouse_timeout_seconds == 12
    assert settings.db_fallback_enabled is False
    assert settings.auth_jwt_secret == "jwt-secret"
    assert settings.auth_jwt_issuer == "issuer"
    assert settings.auth_jwt_audience == "audience"
    assert settings.require_tenant_claim_non_dev is False
    assert settings.metrics_enabled is True
    assert settings.trace_header_name == "X-Request-ID"
    assert settings.pilot_mode_enabled is False
    assert settings.pilot_mode_label == "off"


def test_settings_fail_fast_for_non_dev_unsafe_defaults(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_JWT_SECRET", "dev-secret")
    monkeypatch.setenv("CLICKHOUSE_USER", "default")
    monkeypatch.setenv("CLICKHOUSE_PASSWORD", "")
    monkeypatch.setenv("CLICKHOUSE_URL", "http://localhost:8123")
    monkeypatch.setenv("API_CORS_ORIGINS", "http://localhost:3000")
    monkeypatch.setenv("DB_FALLBACK_ENABLED", "true")
    clear_settings_cache()

    try:
        get_settings()
        assert False, "expected ValueError for unsafe production settings"
    except ValueError as exc:
        assert "staging/production" in str(exc)

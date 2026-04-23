import os

from fastapi.testclient import TestClient

from auth_test_utils import auth_headers as shared_auth_headers
from apps.api.main import app
from apps.api.settings import clear_settings_cache


client = TestClient(app)


def setup_function() -> None:
    os.environ["AUTH_JWT_SECRET"] = "prod-secret"
    os.environ["AUTH_JWT_ISSUER"] = "epi-engine"
    os.environ["AUTH_JWT_AUDIENCE"] = "epi-engine-clients"
    os.environ["APP_ENV"] = "production"
    os.environ["DB_FALLBACK_ENABLED"] = "false"
    os.environ["API_CORS_ORIGINS"] = "https://epios.example.com"
    os.environ["CLICKHOUSE_URL"] = "http://clickhouse:8123"
    os.environ["CLICKHOUSE_USER"] = "epi_engine_app"
    os.environ["CLICKHOUSE_PASSWORD"] = "prod-password"
    clear_settings_cache()
    app.dependency_overrides.clear()


def test_missing_tenant_claim_rejected_in_non_dev() -> None:
    response = client.get("/auth/me", headers=auth_headers(role="analyst", include_tenant=False))
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "tenant_id is required in bearer token claims"


def test_tenant_override_requires_admin_or_operations() -> None:
    response = client.get(
        "/auth/me",
        headers={
            **auth_headers(role="analyst", tenant_id="tenant-a"),
            "X-Tenant-ID": "tenant-b",
        },
    )
    assert response.status_code == 403
    assert "tenant override" in response.json()["error"]["message"]


def auth_headers(role: str, tenant_id: str = "tenant-a", include_tenant: bool = True) -> dict[str, str]:
    return shared_auth_headers(
        role=role,
        tenant_id=tenant_id,
        include_tenant=include_tenant,
        secret="prod-secret",
    )

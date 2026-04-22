import base64
import hashlib
import hmac
import json
import os
import time

from fastapi.testclient import TestClient

from apps.api.audit import clear_audit_events, get_audit_events
from apps.api.main import app
from apps.api.settings import clear_settings_cache


client = TestClient(app)


def setup_function() -> None:
    os.environ["AUTH_JWT_SECRET"] = "dev-secret"
    os.environ["AUTH_JWT_ISSUER"] = "epi-engine"
    os.environ["AUTH_JWT_AUDIENCE"] = "epi-engine-clients"
    clear_audit_events()
    clear_settings_cache()
    app.dependency_overrides.clear()


def test_get_diseases_returns_paginated_items() -> None:
    response = client.get("/diseases", params={"page": 1, "page_size": 1}, headers=auth_headers("analyst"))

    assert response.status_code == 200
    body = response.json()
    assert body["pagination"] == {
        "page": 1,
        "page_size": 1,
        "total_items": 2,
        "total_pages": 2,
    }
    assert len(body["items"]) == 1
    assert body["items"][0]["disease_id"] == "copd"
    assert get_audit_events()[0]["event_name"] == "access.allowed"


def test_get_incidence_filters_by_region_and_year() -> None:
    response = client.get(
        "/incidence",
        params={"region": "US", "year_from": 2025, "year_to": 2025, "page": 1, "page_size": 10},
        headers=auth_headers("payer_aggregate_only"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["total_items"] == 2
    assert {item["disease_id"] for item in body["items"]} == {"t2d", "copd"}
    assert all(item["region_code"] == "US" for item in body["items"])
    assert all(item["year"] == 2025 for item in body["items"])


def test_get_prevalence_rejects_invalid_year_range() -> None:
    response = client.get(
        "/prevalence",
        params={"year_from": 2025, "year_to": 2024},
        headers=auth_headers("read_only_gov"),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_get_top_indications_supports_region_filter_and_pagination() -> None:
    response = client.get(
        "/indications/top",
        params={"region": "US", "limit": 2, "page": 1, "page_size": 1},
        headers=auth_headers("trial_coordinator"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["pagination"] == {
        "page": 1,
        "page_size": 1,
        "total_items": 2,
        "total_pages": 2,
    }
    assert len(body["items"]) == 1
    assert body["items"][0]["indication_id"] == "t2d-us"


def test_indications_top_forbids_payer_aggregate_only() -> None:
    response = client.get("/indications/top", headers=auth_headers("payer_aggregate_only"))

    assert response.status_code == 403
    assert "not allowed" in response.json()["error"]["message"]
    assert get_audit_events()[0]["event_name"] == "access.denied"


def test_missing_authorization_header_returns_401() -> None:
    response = client.get("/diseases")

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "missing Authorization header"
    assert get_audit_events()[0]["payload"]["outcome"] == "denied"


def test_patient_level_export_is_blocked_and_audited() -> None:
    response = client.post("/exports/patient-level", headers=auth_headers("admin", subject="admin-user"))

    assert response.status_code == 403
    assert response.json()["error"]["message"] == "patient-level export is disabled for this platform"
    events = get_audit_events()
    assert events[0]["event_name"] == "access.allowed"
    assert events[1]["event_name"] == "export.attempt"
    assert events[1]["payload"]["outcome"] == "blocked"
    assert events[1]["payload"]["subject"] == "admin-user"


def test_ranked_indications_returns_explanations_and_weights() -> None:
    response = client.get(
        "/indications/ranked",
        params={
            "region": "US",
            "limit": 2,
            "incidence_weight": 0.3,
            "prevalence_weight": 0.2,
            "unmet_need_weight": 0.2,
            "market_size_weight": 0.1,
            "competition_penalty_weight": 0.1,
            "equity_score_weight": 0.1,
        },
        headers=auth_headers("analyst"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["total_items"] == 2
    assert body["items"][0]["indication_id"] == "t2d-us"
    assert len(body["items"][0]["explanations"]) == 6
    assert body["items"][0]["weights_used"]["incidence"] == 0.3
    assert body["items"][0]["explanations"][4]["factor"] == "competition_penalty"


def test_ranked_indications_forbids_read_only_gov() -> None:
    response = client.get("/indications/ranked", headers=auth_headers("read_only_gov"))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "http_error"


def test_unknown_role_claim_is_rejected() -> None:
    response = client.get("/diseases", headers=auth_headers(raw_role="unknown"))

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "role unknown is not recognized"


def test_invalid_token_signature_is_rejected() -> None:
    headers = {"Authorization": f"Bearer {encode_token({'sub': 'user-1', 'role': 'analyst'}, secret='wrong-secret')}"}

    response = client.get("/diseases", headers=headers)

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "invalid bearer token signature"
    assert get_audit_events()[0]["event_name"] == "access.denied"


def test_expired_token_is_rejected() -> None:
    claims = {
        "sub": "user-1",
        "role": "analyst",
        "iss": "epi-engine",
        "aud": "epi-engine-clients",
        "exp": int(time.time()) - 5,
    }
    response = client.get("/diseases", headers={"Authorization": f"Bearer {encode_token(claims)}"})

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "bearer token has expired"


def test_invalid_audience_is_rejected() -> None:
    claims = {
        "sub": "user-1",
        "role": "analyst",
        "iss": "epi-engine",
        "aud": "wrong-audience",
        "exp": int(time.time()) + 3600,
    }
    response = client.get("/diseases", headers={"Authorization": f"Bearer {encode_token(claims)}"})

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "invalid bearer token audience"


def test_invalid_authorization_header_scheme_is_rejected() -> None:
    response = client.get("/diseases", headers={"Authorization": "Token not-a-bearer"})

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "invalid Authorization header"


def test_export_remains_blocked_for_read_only_gov() -> None:
    response = client.post("/exports/patient-level", headers=auth_headers("read_only_gov", subject="gov-user"))

    assert response.status_code == 403
    assert response.json()["error"]["message"] == "patient-level export is disabled for this platform"
    events = get_audit_events()
    assert events[0]["event_name"] == "access.allowed"
    assert events[1]["event_name"] == "export.attempt"
    assert events[1]["payload"]["role"] == "read_only_gov"
    assert events[1]["payload"]["subject"] == "gov-user"


def test_health_includes_environment() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "environment" in response.json()


def auth_headers(role: str | None = None, *, subject: str = "user-1", raw_role: str | None = None) -> dict[str, str]:
    claims = {
        "sub": subject,
        "role": role if raw_role is None else raw_role,
        "iss": "epi-engine",
        "aud": "epi-engine-clients",
        "exp": int(time.time()) + 3600,
    }
    return {"Authorization": f"Bearer {encode_token(claims)}"}


def encode_token(payload: dict[str, object], *, secret: str = "dev-secret") -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    encoded_header = _urlsafe_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _urlsafe_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(
        secret.encode("utf-8"),
        f"{encoded_header}.{encoded_payload}".encode("ascii"),
        hashlib.sha256,
    ).digest()
    encoded_signature = _urlsafe_encode(signature)
    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"


def _urlsafe_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")

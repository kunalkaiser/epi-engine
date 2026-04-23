import os
from datetime import datetime, UTC

from fastapi.testclient import TestClient

from auth_test_utils import auth_headers as shared_auth_headers
from apps.api.audit import clear_audit_events
from apps.api.main import app
from apps.api.platform_models import (
    DataQualityResultStatus,
    SimulationComparisonResponse,
    SimulationDeltaItem,
    SimulationRunSummary,
)
from apps.api.response_models import PaginationMeta
from apps.api.settings import clear_settings_cache


client = TestClient(app)


def setup_function() -> None:
    os.environ["APP_ENV"] = "development"
    os.environ["AUTH_JWT_SECRET"] = "dev-secret"
    os.environ["AUTH_JWT_ISSUER"] = "epi-engine"
    os.environ["AUTH_JWT_AUDIENCE"] = "epi-engine-clients"
    clear_audit_events()
    clear_settings_cache()
    app.dependency_overrides.clear()
    _install_fake_platform_repository()


def test_ready_returns_dependency_statuses() -> None:
    response = client.get("/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert any(item["name"] == "analytics_repository" for item in body["dependencies"])


def test_auth_me_returns_claims() -> None:
    response = client.get("/auth/me", headers=auth_headers("analyst", subject="alice"))

    assert response.status_code == 200
    body = response.json()
    assert body["subject"] == "alice"
    assert body["role"] == "analyst"
    assert body["tenant_id"] == "tenant-a"


def test_mortality_returns_aggregate_rows() -> None:
    response = client.get("/mortality", headers=auth_headers("read_only_gov"))

    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "pagination" in body


def test_determinants_returns_driver_categories() -> None:
    response = client.get("/determinants", headers=auth_headers("analyst"))

    assert response.status_code == 200
    body = response.json()
    assert len(body["drivers"]) >= 1
    assert {item["relationship_type"] for item in body["drivers"]}.issubset(
        {"descriptive", "associative", "causal_hypothesis"}
    )


def test_simulation_run_and_result_roundtrip() -> None:
    run_response = client.post(
        "/simulation/run",
        headers=auth_headers("analyst"),
        json={
            "scenario_type": "weighting_change",
            "region": "US",
            "limit": 2,
            "weights_override": {
                "incidence": 0.3,
                "prevalence": 0.15,
                "unmet_need": 0.25,
                "market_size": 0.15,
                "competition_penalty": 0.1,
                "equity_score": 0.05,
            },
        },
    )
    assert run_response.status_code == 200
    run_id = run_response.json()["run_id"]

    result_response = client.get(f"/simulation/results/{run_id}", headers=auth_headers("analyst"))
    assert result_response.status_code == 200
    result_body = result_response.json()
    assert result_body["run_id"] == run_id
    assert isinstance(result_body["items"], list)


def test_runtime_debug_requires_authorized_role() -> None:
    response = client.get("/debug/runtime", headers=auth_headers("payer_aggregate_only"))
    assert response.status_code == 403


def test_metrics_endpoint_can_be_disabled(monkeypatch) -> None:
    monkeypatch.setenv("API_METRICS_ENABLED", "false")
    clear_settings_cache()
    response = client.get("/metrics")
    assert response.status_code == 404


def test_simulation_runs_lists_tenant_scoped_results() -> None:
    create_response = client.post(
        "/simulation/run",
        headers=auth_headers("analyst"),
        json={"scenario_type": "weighting_change", "region": "US", "limit": 1},
    )
    assert create_response.status_code == 200

    list_response = client.get("/simulation/runs", headers=auth_headers("analyst"))
    assert list_response.status_code == 200
    body = list_response.json()
    assert body["pagination"]["total_items"] >= 1
    assert body["items"][0]["tenant_id"] == "tenant-a"


def test_simulation_cancel_and_compare() -> None:
    create_response = client.post(
        "/simulation/run",
        headers=auth_headers("analyst"),
        json={"scenario_type": "weighting_change", "region": "US", "limit": 1},
    )
    run_id = create_response.json()["run_id"]

    cancel_response = client.post(f"/simulation/runs/{run_id}/cancel", headers=auth_headers("analyst"))
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"

    second = client.post(
        "/simulation/run",
        headers=auth_headers("analyst"),
        json={"scenario_type": "regional_expansion", "region": "US", "limit": 1},
    )
    run_id_2 = second.json()["run_id"]

    compare = client.post(
        "/simulation/compare",
        headers=auth_headers("analyst"),
        json={"run_ids": [run_id, run_id_2]},
    )
    assert compare.status_code == 200
    assert compare.json()["tenant_id"] == "tenant-a"


def test_admin_ingestion_runs_requires_admin_or_ops() -> None:
    denied = client.get("/admin/ingestion-runs", headers=auth_headers("analyst"))
    assert denied.status_code == 403
    allowed = client.get("/admin/ingestion-runs", headers=auth_headers("operations"))
    assert allowed.status_code == 200


def test_data_quality_by_id_works() -> None:
    response = client.get("/data-quality/dq-1", headers=auth_headers("analyst"))
    assert response.status_code == 200
    assert response.json()["result_id"] == "dq-1"


def test_admin_create_data_quality_run() -> None:
    response = client.post(
        "/admin/data-quality-runs",
        headers=auth_headers("operations"),
        json={
            "domain": "incidence",
            "check_type": "freshness_window",
            "severity": "medium",
            "status": "pass",
            "summary_metrics": {"checked_rows": 50},
            "failing_dimensions": [],
            "thresholds": {"max_age_hours": 24},
            "rules_version": "dq-rules-v1",
            "measured_at": datetime.now(UTC).isoformat(),
        },
    )
    assert response.status_code == 200
    assert response.json()["result_id"] == "dq-created-1"


def test_pilot_config_is_available_to_authorized_roles() -> None:
    response = client.get("/pilot/config", headers=auth_headers("analyst"))
    assert response.status_code == 200
    body = response.json()
    assert "enabled" in body
    assert "data_policy" in body
    assert "restrictions" in body


def test_decision_memo_endpoints_return_aggregate_safe_payload() -> None:
    run_response = client.post(
        "/simulation/run",
        headers=auth_headers("analyst"),
        json={
            "scenario_type": "weighting_change",
            "region": "US",
            "limit": 2,
        },
    )
    assert run_response.status_code == 200
    run_id = run_response.json()["run_id"]

    indication_memo = client.get("/reports/decision-memo", headers=auth_headers("analyst"))
    assert indication_memo.status_code == 200
    indication_body = indication_memo.json()
    assert indication_body["result_classification"] == "associative"
    assert "patient" not in indication_body["summary"].lower()
    assert isinstance(indication_body["caveats"], list)

    simulation_memo = client.get(
        f"/reports/simulation/{run_id}/decision-memo",
        headers=auth_headers("analyst"),
    )
    assert simulation_memo.status_code == 200
    simulation_body = simulation_memo.json()
    assert simulation_body["result_classification"] == "scenario_projection"
    assert isinstance(simulation_body["recommendations"], list)


def test_decision_memo_rejects_invalid_query_values() -> None:
    response = client.get(
        "/reports/decision-memo",
        headers=auth_headers("analyst"),
        params={"limit": 0},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def auth_headers(role: str, *, subject: str = "user-1") -> dict[str, str]:
    return shared_auth_headers(role=role, subject=subject, secret="dev-secret")


class _FakePlatformRepository:
    def __init__(self) -> None:
        self.runs: dict[str, dict[str, object]] = {}
        self.counter = 0

    def create_simulation_run(self, **kwargs):
        self.counter += 1
        run_id = f"sim_fake_{self.counter}"
        now = datetime.now(UTC)
        summary = SimulationRunSummary(
            run_id=run_id,
            tenant_id=kwargs["tenant_id"],
            status="queued",
            scenario_type=kwargs["scenario_type"],
            region=kwargs.get("region"),
            created_by=kwargs["created_by"],
            trigger_source=kwargs["trigger_source"],
            methodology=kwargs["methodology"],
            created_at=now,
            updated_at=now,
        )
        self.runs[run_id] = {"summary": summary, "assumptions": kwargs["assumptions"], "items": []}
        return run_id

    def update_simulation_run(self, **kwargs):
        run_id = kwargs["run_id"]
        summary = self.runs[run_id]["summary"]
        assert isinstance(summary, SimulationRunSummary)
        self.runs[run_id]["summary"] = summary.model_copy(
            update={
                "status": kwargs["status"],
                "result_summary": kwargs.get("result_summary"),
                "error_message": kwargs.get("error_message"),
                "updated_at": datetime.now(UTC),
            }
        )

    def save_simulation_result_items(self, **kwargs):
        self.runs[kwargs["run_id"]]["items"] = kwargs["items"]

    def get_simulation_run(self, **kwargs):
        run = self.runs.get(kwargs["run_id"])
        if run is None:
            return None
        return type(
            "SimulationRunRecord",
            (),
            {
                "summary": run["summary"],
                "assumptions": run["assumptions"],
                "items": run["items"],
            },
        )()

    def list_simulation_runs(self, **kwargs):
        return [run["summary"] for run in self.runs.values()], _pagination()

    def cancel_simulation_run(self, **kwargs):
        run = self.runs.get(kwargs["run_id"])
        if run is None:
            return False
        summary = run["summary"]
        assert isinstance(summary, SimulationRunSummary)
        run["summary"] = summary.model_copy(update={"status": "cancelled", "updated_at": datetime.now(UTC)})
        return True

    def compare_simulation_runs(self, **kwargs):
        run_ids = kwargs["request"].run_ids
        return SimulationComparisonResponse(
            tenant_id="tenant-a",
            compared_run_ids=run_ids,
            assumption_deltas={"scenario_type": ["weighting_change", "regional_expansion"]},
            score_deltas=[
                SimulationDeltaItem(
                    indication_id="t2d-us",
                    indication_name="Type 2 diabetes",
                    min_score=61.2,
                    max_score=70.7,
                    score_spread=9.5,
                    run_scores={run_ids[0]: 61.2, run_ids[1]: 70.7},
                )
            ],
            generated_at=datetime.now(UTC),
        )

    def list_data_quality_results(self, **kwargs):
        item = DataQualityResultStatus(
            result_id="dq-1",
            tenant_id="tenant-a",
            domain="incidence",
            check_type="freshness_window",
            severity="medium",
            status="pass",
            summary_metrics={"checked_rows": 10},
            failing_dimensions=[],
            thresholds={"max_age_hours": 24},
            rules_version="dq-rules-v1",
            measured_at=datetime.now(UTC),
            created_by="system",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        return [item], _pagination()

    def get_data_quality_result(self, **kwargs):
        return DataQualityResultStatus(
            result_id=kwargs["result_id"],
            tenant_id="tenant-a",
            domain="incidence",
            check_type="freshness_window",
            severity="medium",
            status="pass",
            summary_metrics={"checked_rows": 10},
            failing_dimensions=[],
            thresholds={"max_age_hours": 24},
            rules_version="dq-rules-v1",
            measured_at=datetime.now(UTC),
            created_by="system",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    def create_data_quality_result(self, **kwargs):
        payload = kwargs["payload"]
        return DataQualityResultStatus(
            result_id="dq-created-1",
            tenant_id=kwargs["tenant_id"],
            domain=payload.domain,
            check_type=payload.check_type,
            severity=payload.severity,
            status=payload.status,
            summary_metrics=payload.summary_metrics,
            failing_dimensions=payload.failing_dimensions,
            thresholds=payload.thresholds,
            rules_version=payload.rules_version,
            ingestion_run_id=payload.ingestion_run_id,
            measured_at=payload.measured_at,
            created_by=kwargs["created_by"],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    def list_ingestion_runs(self, **kwargs):
        return [], _pagination()

    def get_ingestion_run(self, **kwargs):
        return None


def _pagination():
    return PaginationMeta(page=1, page_size=20, total_items=1, total_pages=1)


def _install_fake_platform_repository() -> None:
    import apps.api.platform_services as platform_services

    fake_repository = _FakePlatformRepository()
    platform_services.build_platform_repository = lambda: fake_repository

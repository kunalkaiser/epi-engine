from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from apps.api.response_models import PaginationMeta


class HealthStatusResponse(BaseModel):
    status: Literal["ok", "degraded"]
    environment: str
    service: str = "epios-api"
    timestamp: datetime


class DependencyStatus(BaseModel):
    name: str
    status: Literal["ok", "degraded"]
    detail: str


class ReadyStatusResponse(BaseModel):
    status: Literal["ok", "degraded"]
    dependencies: list[DependencyStatus]
    timestamp: datetime


class AuthMeResponse(BaseModel):
    subject: str
    role: str
    tenant_id: str
    issuer: str | None = None
    audience: str | None = None
    expires_at: int | None = None


class MethodologyMetadata(BaseModel):
    method_name: str
    methodology_version: str
    assumptions_summary: str
    assumptions_registry: list[str] = Field(default_factory=list)
    data_inputs_summary: str
    input_limitations: list[str] = Field(default_factory=list)
    confidence_summary: str
    uncertainty_semantics: str = "Uncertainty bounds reflect scenario sensitivity, not causal certainty."
    causal_labeling_policy: str
    result_classification: Literal["descriptive", "associative", "causal_hypothesis", "scenario_projection"] = "associative"
    caveats: list[str] = Field(default_factory=list)
    generated_at: datetime


class MortalityAggregate(BaseModel):
    disease_id: str = Field(min_length=1, max_length=64)
    disease_name: str = Field(min_length=1, max_length=160)
    region_code: str = Field(min_length=2, max_length=16)
    year: int = Field(ge=1900, le=2100)
    deaths: int = Field(ge=0)
    population: int = Field(gt=0)
    mortality_per_100k: float = Field(ge=0)

    model_config = ConfigDict(str_strip_whitespace=True)


class MortalityResponse(BaseModel):
    items: list[MortalityAggregate]
    pagination: PaginationMeta


class DeterminantDriver(BaseModel):
    factor: str
    category: Literal["clinical", "biomarker", "social", "environmental"]
    relationship_type: Literal["descriptive", "associative", "causal_hypothesis"]
    result_classification: Literal["descriptive", "associative", "causal_hypothesis"]
    contribution_score: float = Field(ge=0, le=100)
    confidence: Literal["low", "medium", "high"]
    uncertainty_note: str


class DeterminantsResponse(BaseModel):
    disease_id: str | None = None
    region: str | None = None
    period: str
    drivers: list[DeterminantDriver]
    methodology: MethodologyMetadata
    pagination: PaginationMeta


SimulationRunStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]


class SimulationRunRequest(BaseModel):
    scenario_type: Literal["subpopulation_targeting", "regional_expansion", "trial_feasibility", "weighting_change"]
    region: str | None = None
    limit: int = Field(default=10, ge=1, le=100)
    assumptions: dict[str, Any] = Field(default_factory=dict)
    weights_override: dict[str, float] = Field(default_factory=dict)


class SimulationResultItem(BaseModel):
    indication_id: str
    indication_name: str
    baseline_score: float = Field(ge=0, le=100)
    simulated_score: float = Field(ge=0, le=100)
    score_delta: float
    uncertainty_low: float = Field(ge=0, le=100)
    uncertainty_high: float = Field(ge=0, le=100)
    outcome_drivers: list[str] = Field(default_factory=list)
    score_inputs: dict[str, float] = Field(default_factory=dict)
    trace_id: str
    result_classification: Literal["scenario_projection"] = "scenario_projection"
    caveats: list[str] = Field(default_factory=list)


class SimulationRunSummary(BaseModel):
    run_id: str
    tenant_id: str
    status: SimulationRunStatus
    scenario_type: str
    region: str | None = None
    created_by: str
    trigger_source: str
    result_summary: str | None = None
    artifact_ref: str | None = None
    error_message: str | None = None
    methodology: MethodologyMetadata
    created_at: datetime
    updated_at: datetime
    attempt_count: int = Field(ge=0, default=0)
    max_attempts: int = Field(ge=1, le=10, default=2)


class SimulationRunResponse(BaseModel):
    run: SimulationRunSummary
    run_id: str
    status: SimulationRunStatus
    created_at: datetime
    summary: str | None = None


class SimulationRunCancelResponse(BaseModel):
    run_id: str
    status: Literal["cancelled"]


class SimulationResultResponse(BaseModel):
    run: SimulationRunSummary
    assumptions: dict[str, Any]
    items: list[SimulationResultItem]
    run_id: str
    scenario_type: str


class SimulationRunsResponse(BaseModel):
    items: list[SimulationRunSummary]
    pagination: PaginationMeta


class SimulationRunCompareRequest(BaseModel):
    run_ids: list[str] = Field(min_length=2, max_length=5)


class SimulationDeltaItem(BaseModel):
    indication_id: str
    indication_name: str
    min_score: float
    max_score: float
    score_spread: float
    run_scores: dict[str, float]


class SimulationComparisonResponse(BaseModel):
    tenant_id: str
    compared_run_ids: list[str]
    assumption_deltas: dict[str, list[str]]
    score_deltas: list[SimulationDeltaItem]
    generated_at: datetime


class IngestionRunStatusSummary(BaseModel):
    run_id: str
    tenant_id: str
    dataset_name: str
    source_system: str
    trigger_source: Literal["scheduled", "manual", "backfill"]
    status: Literal["queued", "running", "succeeded", "failed", "cancelled"]
    records_processed: int = Field(ge=0)
    records_inserted: int = Field(ge=0)
    records_updated: int = Field(ge=0)
    records_rejected: int = Field(ge=0)
    validation_summary: dict[str, Any] = Field(default_factory=dict)
    error_summary: dict[str, Any] = Field(default_factory=dict)
    freshness_metric: str | None = None
    provenance_ref: str | None = None
    artifact_ref: str | None = None
    created_by: str
    started_at: datetime
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class IngestionRunsResponse(BaseModel):
    items: list[IngestionRunStatusSummary]
    pagination: PaginationMeta


class DataQualityResultStatus(BaseModel):
    result_id: str
    tenant_id: str
    domain: str
    check_type: str
    severity: Literal["low", "medium", "high", "critical"]
    status: Literal["pass", "warn", "fail"]
    summary_metrics: dict[str, Any] = Field(default_factory=dict)
    failing_dimensions: list[str] = Field(default_factory=list)
    thresholds: dict[str, Any] = Field(default_factory=dict)
    rules_version: str
    ingestion_run_id: str | None = None
    measured_at: datetime
    created_by: str
    created_at: datetime
    updated_at: datetime


class DataQualityResponse(BaseModel):
    status: Literal["ok", "degraded"]
    items: list[DataQualityResultStatus]
    pagination: PaginationMeta
    generated_at: datetime


class DataQualityRunsResponse(BaseModel):
    items: list[DataQualityResultStatus]
    pagination: PaginationMeta


class DataQualityUpsertRequest(BaseModel):
    domain: str = Field(min_length=1, max_length=64)
    check_type: str = Field(min_length=1, max_length=64)
    severity: Literal["low", "medium", "high", "critical"]
    status: Literal["pass", "warn", "fail"]
    summary_metrics: dict[str, Any] = Field(default_factory=dict)
    failing_dimensions: list[str] = Field(default_factory=list)
    thresholds: dict[str, Any] = Field(default_factory=dict)
    rules_version: str = Field(min_length=1, max_length=64)
    ingestion_run_id: str | None = None
    measured_at: datetime


class AuditEventsResponse(BaseModel):
    items: list[dict[str, Any]]
    pagination: PaginationMeta


class RuntimeDebugResponse(BaseModel):
    environment: str
    fallback_enabled: bool
    clickhouse_url_present: bool
    auth_configured: bool
    tenant_claim_required_non_dev: bool
    metrics_enabled: bool
    trace_header_name: str
    queued_simulation_runs: int | None = None
    pilot_mode_enabled: bool = False
    pilot_mode_label: str = "off"
    timestamp: datetime


class PilotModeResponse(BaseModel):
    enabled: bool
    label: str
    mode_description: str
    data_policy: str
    restrictions: list[str]
    generated_at: datetime


class DecisionMemoResponse(BaseModel):
    title: str
    tenant_id: str
    generated_at: datetime
    result_classification: Literal["descriptive", "associative", "causal_hypothesis", "scenario_projection"]
    summary: str
    key_points: list[str]
    methodology: dict[str, Any]
    caveats: list[str]
    recommendations: list[str]


class MethodologyResponse(BaseModel):
    model_version: str
    scoring: dict[str, Any]
    determinants: dict[str, Any]
    simulation: dict[str, Any]
    generated_at: datetime

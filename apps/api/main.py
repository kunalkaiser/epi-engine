import logging
from uuid import uuid4
from datetime import UTC, datetime

from fastapi.encoders import jsonable_encoder
from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from apps.api.audit import audit_log, audit_log_export
from apps.api.db import ClickHouseUnavailableError
from apps.api.logging_utils import configure_logging, get_logger, log_event
from apps.api.query_models import (
    DataQualityRunsFilters,
    IngestionRunsFilters,
    PaginationParams,
    RankedIndicationsFilters,
    RegionTimeFilters,
    SimulationRunsFilters,
    TopIndicationsFilters,
    data_quality_runs_filters_dependency,
    ingestion_runs_filters_dependency,
    pagination_params_dependency,
    ranked_indications_filters_dependency,
    region_time_filters_dependency,
    simulation_runs_filters_dependency,
    top_indications_filters_dependency,
)
from apps.api.platform_models import (
    AuditEventsResponse,
    AuthMeResponse,
    DataQualityResponse,
    DataQualityResultStatus,
    DataQualityRunsResponse,
    DataQualityUpsertRequest,
    DeterminantsResponse,
    HealthStatusResponse,
    IngestionRunStatusSummary,
    IngestionRunsResponse,
    MethodologyResponse,
    MortalityResponse,
    ReadyStatusResponse,
    RuntimeDebugResponse,
    SimulationResultResponse,
    SimulationRunRequest,
    SimulationRunResponse,
    SimulationRunCancelResponse,
    SimulationRunsResponse,
    SimulationRunCompareRequest,
    SimulationComparisonResponse,
    PilotModeResponse,
    DecisionMemoResponse,
)
from apps.api.platform_services import (
    cancel_simulation_run,
    compare_simulation_runs,
    get_audit_events_page,
    get_auth_me,
    get_data_quality,
    get_data_quality_result,
    get_determinants,
    get_ingestion_run,
    get_methodology,
    get_ready_status,
    get_runtime_debug,
    get_simulation_result,
    list_data_quality_runs,
    list_ingestion_runs,
    list_mortality,
    list_simulation_runs,
    run_simulation,
    create_data_quality_result,
    get_pilot_mode_config,
    generate_indication_decision_memo,
    generate_simulation_decision_memo,
)
from apps.api.settings import get_settings
from apps.api.response_models import (
    DiseasesResponse,
    IncidenceResponse,
    PrevalenceResponse,
    RankedIndicationsResponse,
    RepurposingOpportunitiesResponse,
    TopIndicationsResponse,
)
from apps.api.security import AuthClaims, RequestContext, Role, require_authenticated_claims, require_request_context, require_role
from apps.api.services import list_diseases, list_incidence, list_prevalence, list_ranked_indications, list_repurposing_opportunities, list_top_indications

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger("epi_engine.api")

AGGREGATE_READER_ROLES: set[Role] = {"admin", "analyst", "payer_aggregate_only", "trial_coordinator", "read_only_gov"}
INDICATION_ROLES: set[Role] = {"admin", "analyst", "trial_coordinator"}
AUTH_ME_ROLES: set[Role] = {
    "admin",
    "analyst",
    "read_only",
    "auditor",
    "operations",
    "payer_aggregate_only",
    "trial_coordinator",
    "read_only_gov",
}
SIMULATION_RUN_ROLES: set[Role] = {"admin", "analyst", "operations", "trial_coordinator"}
SIMULATION_RESULT_ROLES: set[Role] = {
    "admin",
    "analyst",
    "operations",
    "trial_coordinator",
    "read_only",
    "read_only_gov",
    "auditor",
}
SIMULATION_COMPARE_ROLES: set[Role] = {"admin", "operations", "analyst", "trial_coordinator", "auditor"}
DATA_QUALITY_ROLES: set[Role] = {
    "admin",
    "analyst",
    "operations",
    "payer_aggregate_only",
    "trial_coordinator",
    "read_only_gov",
    "read_only",
    "auditor",
}
ADMIN_DATA_ROLES: set[Role] = {"admin", "operations", "auditor"}
REPORT_ROLES: set[Role] = {"admin", "analyst", "operations", "trial_coordinator", "auditor"}

# ── Rate limiter ──────────────────────────────────────────────────────────────
# 200 req/min per IP globally; burst-sensitive endpoints get tighter limits via
# @limiter.limit() decorator. Limits are per-IP — authenticated clients hitting
# the same egress IP share a bucket (acceptable given JWT-auth enforcement).
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

app = FastAPI(title="EPI Engine API")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SlowAPIMiddleware)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    runtime_settings = get_settings()
    correlation_id = request.headers.get(runtime_settings.trace_header_name) or str(uuid4())
    request.state.correlation_id = correlation_id
    log_event(
        logger,
        logging.INFO,
        "request.started",
        method=request.method,
        path=request.url.path,
        correlation_id=correlation_id,
    )
    try:
        response = await call_next(request)
    except Exception:
        log_event(
            logger,
            logging.ERROR,
            "request.failed",
            method=request.method,
            path=request.url.path,
            correlation_id=correlation_id,
        )
        raise
    log_event(
        logger,
        logging.INFO,
        "request.completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        correlation_id=correlation_id,
    )
    response.headers[runtime_settings.trace_header_name] = correlation_id
    if runtime_settings.trace_header_name.lower() != "x-request-id":
        response.headers["X-Request-ID"] = correlation_id
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    log_event(logger, logging.WARNING, "request.validation_error", errors=len(exc.errors()))
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "validation_error",
                "message": "Request validation failed",
                "details": jsonable_encoder(exc.errors()),
            }
        },
    )


@app.exception_handler(ClickHouseUnavailableError)
async def clickhouse_unavailable_handler(_: Request, exc: ClickHouseUnavailableError) -> JSONResponse:
    # Analytics datastore (ClickHouse) unreachable. Return a clean 503 instead of letting it
    # bubble to the catch-all 500 handler — which runs in Starlette's outermost
    # ServerErrorMiddleware, OUTSIDE CORSMiddleware, so its response carries no CORS headers and
    # the browser reports it as a CORS error. A specific handler like this runs in the inner
    # ExceptionMiddleware, so CORSMiddleware still applies and the client degrades gracefully.
    log_event(logger, logging.WARNING, "request.clickhouse_unavailable")
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": {
                "code": "data_unavailable",
                "message": "Analytics datastore temporarily unavailable",
            }
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    log_event(logger, logging.WARNING, "request.http_error", status_code=exc.status_code, detail=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "http_error",
                "message": exc.detail,
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    log_event(logger, logging.ERROR, "request.unhandled_error", error_type=type(exc).__name__)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "internal_error",
                "message": "Internal server error",
            }
        },
    )


@app.get("/health")
def health() -> HealthStatusResponse:
    runtime_settings = get_settings()
    return HealthStatusResponse(
        status="ok",
        environment=runtime_settings.app_env,
        timestamp=datetime.now(UTC),
    )


@app.get("/ready", response_model=ReadyStatusResponse)
def ready() -> ReadyStatusResponse:
    return get_ready_status()


@app.get("/metrics")
def metrics() -> PlainTextResponse:
    runtime_settings = get_settings()
    if not runtime_settings.metrics_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="metrics endpoint is disabled")
    ready_status = get_ready_status()
    payload = [
        "# HELP epios_api_up API process is running",
        "# TYPE epios_api_up gauge",
        "epios_api_up 1",
        "# HELP epios_api_ready API readiness (1=ready, 0=degraded)",
        "# TYPE epios_api_ready gauge",
        f"epios_api_ready {1 if ready_status.status == 'ok' else 0}",
    ]
    return PlainTextResponse("\n".join(payload) + "\n", media_type="text/plain; version=0.0.4")


@app.get("/diseases", response_model=DiseasesResponse)
def get_diseases(
    params: PaginationParams = Depends(pagination_params_dependency),
    _: Role = Depends(require_role("diseases", AGGREGATE_READER_ROLES)),
) -> DiseasesResponse:
    audit_log("diseases.list", payload=params.model_dump(exclude_none=True))
    return list_diseases(params)


@app.get("/incidence", response_model=IncidenceResponse)
def get_incidence(
    filters: RegionTimeFilters = Depends(region_time_filters_dependency),
    _: Role = Depends(require_role("incidence", AGGREGATE_READER_ROLES)),
) -> IncidenceResponse:
    audit_log("incidence.list", payload=filters.model_dump(exclude_none=True))
    return list_incidence(filters)


@app.get("/prevalence", response_model=PrevalenceResponse)
def get_prevalence(
    filters: RegionTimeFilters = Depends(region_time_filters_dependency),
    _: Role = Depends(require_role("prevalence", AGGREGATE_READER_ROLES)),
) -> PrevalenceResponse:
    audit_log("prevalence.list", payload=filters.model_dump(exclude_none=True))
    return list_prevalence(filters)


@app.get("/mortality", response_model=MortalityResponse)
def get_mortality(
    filters: RegionTimeFilters = Depends(region_time_filters_dependency),
    _: Role = Depends(require_role("mortality", AGGREGATE_READER_ROLES)),
) -> MortalityResponse:
    audit_log("mortality.list", payload=filters.model_dump(exclude_none=True))
    return list_mortality(filters)


@app.get("/indications/top", response_model=TopIndicationsResponse)
@limiter.limit("60/minute")
def get_top_indications(
    request: Request,
    filters: TopIndicationsFilters = Depends(top_indications_filters_dependency),
    _: Role = Depends(require_role("indications.top", INDICATION_ROLES)),
) -> TopIndicationsResponse:
    audit_log("indications.top", payload=filters.model_dump(exclude_none=True))
    return list_top_indications(filters)


@app.get("/indications/ranked", response_model=RankedIndicationsResponse)
@limiter.limit("60/minute")
def get_ranked_indications(
    request: Request,
    filters: RankedIndicationsFilters = Depends(ranked_indications_filters_dependency),
    _: Role = Depends(require_role("indications.ranked", INDICATION_ROLES)),
) -> RankedIndicationsResponse:
    audit_log("indications.ranked", payload=filters.model_dump(exclude_none=True))
    return list_ranked_indications(filters)


@app.get("/repurposing/opportunities", response_model=RepurposingOpportunitiesResponse)
@limiter.limit("30/minute")
def get_repurposing_opportunities(
    request: Request,
    _: Role = Depends(require_role("repurposing.opportunities", INDICATION_ROLES)),
) -> RepurposingOpportunitiesResponse:
    """
    Opportunity scanner: top 20 indication+compound pairs with
    high unmet need + low competition + mechanistic rationale.
    Compound candidates fetched from evidence-os repurposing gap analysis.
    """
    audit_log("repurposing.opportunities", payload={})
    return list_repurposing_opportunities()


@app.get("/auth/me", response_model=AuthMeResponse)
def auth_me(
    claims: AuthClaims = Depends(require_authenticated_claims("auth.me")),
    context: RequestContext = Depends(require_request_context("auth.me", AUTH_ME_ROLES)),
) -> AuthMeResponse:
    return get_auth_me(claims, context)


@app.get("/determinants", response_model=DeterminantsResponse)
def get_determinants_route(
    filters: RegionTimeFilters = Depends(region_time_filters_dependency),
    _: Role = Depends(require_role("determinants", AGGREGATE_READER_ROLES)),
) -> DeterminantsResponse:
    audit_log("determinants.list", payload=filters.model_dump(exclude_none=True))
    return get_determinants(filters)


@app.post("/simulation/run", response_model=SimulationRunResponse)
def run_simulation_route(
    payload: SimulationRunRequest,
    context: RequestContext = Depends(require_request_context("simulation.run", SIMULATION_RUN_ROLES)),
) -> SimulationRunResponse:
    audit_log("simulation.run", payload=payload.model_dump(exclude_none=True))
    return run_simulation(payload, context=context)


@app.get("/simulation/results/{run_id}", response_model=SimulationResultResponse)
def get_simulation_result_route(
    run_id: str,
    context: RequestContext = Depends(require_request_context("simulation.results", SIMULATION_RESULT_ROLES)),
) -> SimulationResultResponse:
    result = get_simulation_result(run_id, context=context)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"simulation run not found: {run_id}")
    return result


@app.get("/simulation/runs", response_model=SimulationRunsResponse)
def list_simulation_runs_route(
    filters: SimulationRunsFilters = Depends(simulation_runs_filters_dependency),
    context: RequestContext = Depends(require_request_context("simulation.runs", SIMULATION_COMPARE_ROLES)),
) -> SimulationRunsResponse:
    return list_simulation_runs(context=context, filters=filters)


@app.post("/simulation/runs/{run_id}/cancel", response_model=SimulationRunCancelResponse)
def cancel_simulation_run_route(
    run_id: str,
    context: RequestContext = Depends(require_request_context("simulation.cancel", SIMULATION_RUN_ROLES)),
) -> SimulationRunCancelResponse:
    cancelled = cancel_simulation_run(run_id, context=context)
    if not cancelled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"simulation run cannot be cancelled: {run_id}")
    return SimulationRunCancelResponse(run_id=run_id, status="cancelled")


@app.post("/simulation/compare", response_model=SimulationComparisonResponse)
def compare_simulation_runs_route(
    payload: SimulationRunCompareRequest,
    context: RequestContext = Depends(require_request_context("simulation.compare", SIMULATION_COMPARE_ROLES)),
) -> SimulationComparisonResponse:
    try:
        return compare_simulation_runs(payload, context=context)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@app.get("/methodology", response_model=MethodologyResponse)
def methodology(
    _: Role = Depends(require_role("methodology", AGGREGATE_READER_ROLES)),
) -> MethodologyResponse:
    return get_methodology()


@app.get("/data-quality", response_model=DataQualityResponse)
def data_quality(
    filters: DataQualityRunsFilters = Depends(data_quality_runs_filters_dependency),
    context: RequestContext = Depends(require_request_context("data_quality", DATA_QUALITY_ROLES)),
) -> DataQualityResponse:
    return get_data_quality(context=context, filters=filters)


@app.get("/data-quality/{result_id}", response_model=DataQualityResultStatus)
def data_quality_by_id(
    result_id: str,
    context: RequestContext = Depends(require_request_context("data_quality.read", DATA_QUALITY_ROLES)),
) -> DataQualityResultStatus:
    result = get_data_quality_result(result_id=result_id, context=context)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"data quality result not found: {result_id}")
    return result


@app.get("/admin/data-quality-runs", response_model=DataQualityRunsResponse)
def admin_data_quality_runs(
    filters: DataQualityRunsFilters = Depends(data_quality_runs_filters_dependency),
    context: RequestContext = Depends(require_request_context("admin.data_quality_runs", ADMIN_DATA_ROLES)),
) -> DataQualityRunsResponse:
    return list_data_quality_runs(context=context, filters=filters)


@app.post("/admin/data-quality-runs", response_model=DataQualityResultStatus)
def admin_create_data_quality_run(
    payload: DataQualityUpsertRequest,
    context: RequestContext = Depends(require_request_context("admin.data_quality_runs.create", {"admin", "operations"})),
) -> DataQualityResultStatus:
    return create_data_quality_result(context=context, payload=payload)


@app.get("/admin/ingestion-runs", response_model=IngestionRunsResponse)
def admin_ingestion_runs(
    filters: IngestionRunsFilters = Depends(ingestion_runs_filters_dependency),
    context: RequestContext = Depends(require_request_context("admin.ingestion_runs", ADMIN_DATA_ROLES)),
) -> IngestionRunsResponse:
    return list_ingestion_runs(context=context, filters=filters)


@app.get("/admin/ingestion-runs/{run_id}", response_model=IngestionRunStatusSummary)
def admin_ingestion_run_by_id(
    run_id: str,
    context: RequestContext = Depends(require_request_context("admin.ingestion_run", ADMIN_DATA_ROLES)),
) -> IngestionRunStatusSummary:
    result = get_ingestion_run(run_id=run_id, context=context)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"ingestion run not found: {run_id}")
    return result


@app.get("/audit/events", response_model=AuditEventsResponse)
def audit_events(
    params: PaginationParams = Depends(pagination_params_dependency),
    _: Role = Depends(require_role("audit.events", {"admin", "analyst", "read_only_gov"})),
) -> AuditEventsResponse:
    items, pagination = get_audit_events_page(params.page, params.page_size)
    return AuditEventsResponse(items=items, pagination=pagination)


@app.get("/debug/runtime", response_model=RuntimeDebugResponse)
def debug_runtime(
    _: Role = Depends(require_role("debug.runtime", {"admin", "analyst"})),
) -> RuntimeDebugResponse:
    return get_runtime_debug()


@app.get("/pilot/config", response_model=PilotModeResponse)
def pilot_config(
    _: Role = Depends(require_role("pilot.config", {"admin", "analyst", "operations", "auditor"})),
) -> PilotModeResponse:
    return get_pilot_mode_config()


@app.get("/reports/decision-memo", response_model=DecisionMemoResponse)
def indication_decision_memo(
    region: str | None = Query(default=None, min_length=2, max_length=16),
    limit: int = Query(default=5, ge=1, le=100),
    profile_id: str = Query(default="default_v1", min_length=1, max_length=64),
    context: RequestContext = Depends(require_request_context("reports.decision_memo", REPORT_ROLES)),
) -> DecisionMemoResponse:
    audit_log("reports.decision_memo", payload={"region": region, "limit": limit, "profile_id": profile_id})
    return generate_indication_decision_memo(
        context=context,
        region=region,
        limit=limit,
        profile_id=profile_id,
    )


@app.get("/reports/simulation/{run_id}/decision-memo", response_model=DecisionMemoResponse)
def simulation_decision_memo(
    run_id: str,
    context: RequestContext = Depends(require_request_context("reports.simulation_decision_memo", REPORT_ROLES)),
) -> DecisionMemoResponse:
    audit_log("reports.simulation_decision_memo", payload={"run_id": run_id})
    memo = generate_simulation_decision_memo(run_id=run_id, context=context)
    if memo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"simulation run not found: {run_id}")
    return memo


@app.post("/exports/patient-level")
def export_patient_level(
    claims: AuthClaims = Depends(require_authenticated_claims("exports.patient_level")),
) -> dict[str, str]:
    detail = "patient-level export is disabled for this platform"
    audit_log_export(
        role=claims.role,
        export_type="patient_level",
        outcome="blocked",
        detail=detail,
        subject=claims.sub,
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=detail,
    )

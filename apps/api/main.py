import logging

from fastapi.encoders import jsonable_encoder
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from apps.api.audit import audit_log, audit_log_export
from apps.api.logging_utils import configure_logging, get_logger, log_event
from apps.api.query_models import (
    PaginationParams,
    RankedIndicationsFilters,
    RegionTimeFilters,
    TopIndicationsFilters,
    pagination_params_dependency,
    ranked_indications_filters_dependency,
    region_time_filters_dependency,
    top_indications_filters_dependency,
)
from apps.api.settings import get_settings
from apps.api.response_models import (
    DiseasesResponse,
    IncidenceResponse,
    PrevalenceResponse,
    RankedIndicationsResponse,
    TopIndicationsResponse,
)
from apps.api.security import AuthClaims, Role, require_authenticated_claims, require_role
from apps.api.services import list_diseases, list_incidence, list_prevalence, list_ranked_indications, list_top_indications

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger("epi_engine.api")

app = FastAPI(title="EPI Engine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    log_event(logger, logging.INFO, "request.started", method=request.method, path=request.url.path)
    try:
        response = await call_next(request)
    except Exception:
        log_event(logger, logging.ERROR, "request.failed", method=request.method, path=request.url.path)
        raise
    log_event(
        logger,
        logging.INFO,
        "request.completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
    )
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    log_event(logger, logging.WARNING, "request.validation_error", errors=len(exc.errors()))
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "error": {
                "code": "validation_error",
                "message": "Request validation failed",
                "details": jsonable_encoder(exc.errors()),
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
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}


@app.get("/diseases", response_model=DiseasesResponse)
def get_diseases(
    params: PaginationParams = Depends(pagination_params_dependency),
    _: Role = Depends(
        require_role(
            "diseases",
            {"admin", "analyst", "payer_aggregate_only", "trial_coordinator", "read_only_gov"},
        )
    ),
) -> DiseasesResponse:
    audit_log("diseases.list", payload=params.model_dump(exclude_none=True))
    return list_diseases(params)


@app.get("/incidence", response_model=IncidenceResponse)
def get_incidence(
    filters: RegionTimeFilters = Depends(region_time_filters_dependency),
    _: Role = Depends(
        require_role(
            "incidence",
            {"admin", "analyst", "payer_aggregate_only", "trial_coordinator", "read_only_gov"},
        )
    ),
) -> IncidenceResponse:
    audit_log("incidence.list", payload=filters.model_dump(exclude_none=True))
    return list_incidence(filters)


@app.get("/prevalence", response_model=PrevalenceResponse)
def get_prevalence(
    filters: RegionTimeFilters = Depends(region_time_filters_dependency),
    _: Role = Depends(
        require_role(
            "prevalence",
            {"admin", "analyst", "payer_aggregate_only", "trial_coordinator", "read_only_gov"},
        )
    ),
) -> PrevalenceResponse:
    audit_log("prevalence.list", payload=filters.model_dump(exclude_none=True))
    return list_prevalence(filters)


@app.get("/indications/top", response_model=TopIndicationsResponse)
def get_top_indications(
    filters: TopIndicationsFilters = Depends(top_indications_filters_dependency),
    _: Role = Depends(require_role("indications.top", {"admin", "analyst", "trial_coordinator"})),
) -> TopIndicationsResponse:
    audit_log("indications.top", payload=filters.model_dump(exclude_none=True))
    return list_top_indications(filters)


@app.get("/indications/ranked", response_model=RankedIndicationsResponse)
def get_ranked_indications(
    filters: RankedIndicationsFilters = Depends(ranked_indications_filters_dependency),
    _: Role = Depends(require_role("indications.ranked", {"admin", "analyst", "trial_coordinator"})),
) -> RankedIndicationsResponse:
    audit_log("indications.ranked", payload=filters.model_dump(exclude_none=True))
    return list_ranked_indications(filters)


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

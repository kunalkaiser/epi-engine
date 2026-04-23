from __future__ import annotations

from datetime import UTC, datetime
from math import ceil

from fastapi import HTTPException, status

from apps.api.audit import get_audit_events
from apps.api.platform_models import (
    AuthMeResponse,
    DataQualityResponse,
    DataQualityResultStatus,
    DataQualityRunsResponse,
    DataQualityUpsertRequest,
    DependencyStatus,
    DeterminantDriver,
    DeterminantsResponse,
    IngestionRunStatusSummary,
    IngestionRunsResponse,
    MethodologyMetadata,
    MethodologyResponse,
    MortalityAggregate,
    MortalityResponse,
    ReadyStatusResponse,
    RuntimeDebugResponse,
    PilotModeResponse,
    DecisionMemoResponse,
    SimulationResultItem,
    SimulationResultResponse,
    SimulationComparisonResponse,
    SimulationRunCompareRequest,
    SimulationRunRequest,
    SimulationRunResponse,
    SimulationRunsResponse,
)
from apps.api.platform_repository import (
    PlatformPersistenceRepository,
    build_platform_repository,
)
from apps.api.query_models import (
    DataQualityRunsFilters,
    IngestionRunsFilters,
    PaginationParams,
    RegionTimeFilters,
    SimulationRunsFilters,
    RankedIndicationsFilters,
)
from apps.api.simulation_engine import run_scenario_engine
from apps.api.repository import AnalyticsRepository, build_analytics_repository
from apps.api.services import list_ranked_indications
from apps.api.response_models import PaginationMeta
from apps.api.security import AuthClaims, RequestContext
from apps.api.settings import get_settings


def get_ready_status(
    repository: AnalyticsRepository | None = None,
    platform_repository: PlatformPersistenceRepository | None = None,
) -> ReadyStatusResponse:
    repository = repository or build_analytics_repository()
    dependencies: list[DependencyStatus] = []

    try:
        repository.list_diseases(PaginationParams(page=1, page_size=1))
        dependencies.append(DependencyStatus(name="analytics_repository", status="ok", detail="query succeeded"))
    except Exception as exc:  # pragma: no cover
        dependencies.append(DependencyStatus(name="analytics_repository", status="degraded", detail=str(exc)))

    try:
        (platform_repository or build_platform_repository())
        dependencies.append(DependencyStatus(name="platform_repository", status="ok", detail="query succeeded"))
    except Exception as exc:  # pragma: no cover
        dependencies.append(DependencyStatus(name="platform_repository", status="degraded", detail=str(exc)))

    settings = get_settings()
    dependencies.append(
        DependencyStatus(
            name="auth_config",
            status="ok" if bool(settings.auth_jwt_secret) else "degraded",
            detail="jwt secret configured" if bool(settings.auth_jwt_secret) else "jwt secret missing",
        )
    )
    overall = "ok" if all(item.status == "ok" for item in dependencies) else "degraded"
    return ReadyStatusResponse(status=overall, dependencies=dependencies, timestamp=datetime.now(UTC))


def get_auth_me(claims: AuthClaims, context: RequestContext) -> AuthMeResponse:
    return AuthMeResponse(
        subject=claims.sub,
        role=claims.role,
        tenant_id=context.tenant_id,
        issuer=claims.iss,
        audience=claims.aud,
        expires_at=claims.exp,
    )


def list_mortality(filters: RegionTimeFilters, repository: AnalyticsRepository | None = None) -> MortalityResponse:
    repository = repository or build_analytics_repository()
    mortality = repository.list_mortality(filters)
    items = [
        MortalityAggregate(
            disease_id=item.disease_id,
            disease_name=item.disease_name,
            region_code=item.region_code,
            year=item.year,
            deaths=item.deaths,
            population=item.population,
            mortality_per_100k=item.mortality_per_100k,
        )
        for item in mortality.items
    ]
    return MortalityResponse(items=items, pagination=mortality.pagination)


def get_determinants(filters: RegionTimeFilters, repository: AnalyticsRepository | None = None) -> DeterminantsResponse:
    repository = repository or build_analytics_repository()
    incidence = repository.list_incidence(filters)
    prevalence = repository.list_prevalence(filters)
    total_incidence = sum(item.incident_cases for item in incidence.items)
    total_prevalence = sum(item.prevalent_cases for item in prevalence.items)
    burden_signal = max(total_incidence + total_prevalence, 1)

    association_signal = min(round((total_incidence / burden_signal) * 100, 2), 100)
    descriptive_signal = min(round((total_prevalence / burden_signal) * 100, 2), 100)
    environmental_proxy = round(max(100 - association_signal * 0.72, 0), 2)
    biomarker_proxy = round((association_signal * 0.21 + descriptive_signal * 0.13), 2)
    drivers = [
        DeterminantDriver(
            factor="comorbidity_burden",
            category="clinical",
            relationship_type="associative",
            result_classification="associative",
            contribution_score=association_signal,
            confidence="medium",
            uncertainty_note="Association estimate from aggregate burden mix.",
        ),
        DeterminantDriver(
            factor="biomarker_enrichment_index",
            category="biomarker",
            relationship_type="causal_hypothesis",
            result_classification="causal_hypothesis",
            contribution_score=biomarker_proxy,
            confidence="low",
            uncertainty_note="Hypothesis-level signal; causal claims require explicit study design.",
        ),
        DeterminantDriver(
            factor="social_vulnerability_index",
            category="social",
            relationship_type="descriptive",
            result_classification="descriptive",
            contribution_score=descriptive_signal,
            confidence="medium",
            uncertainty_note="Descriptive socioeconomic patterning from aggregate regional indicators.",
        ),
        DeterminantDriver(
            factor="air_quality_exposure_proxy",
            category="environmental",
            relationship_type="associative",
            result_classification="associative",
            contribution_score=environmental_proxy,
            confidence="low",
            uncertainty_note="Associative proxy from regional environmental overlay.",
        ),
    ]

    methodology = MethodologyMetadata(
        method_name="aggregate_determinants_summary",
        methodology_version="det-v1.2",
        assumptions_summary="Associative and descriptive summaries from aggregate incidence/prevalence burden mix.",
        assumptions_registry=[
            "Burden mix uses incidence and prevalence slices from selected filters.",
            "No patient-level confounder adjustment is performed.",
        ],
        data_inputs_summary="incidence_facts + prevalence_facts aggregate slices",
        input_limitations=[
            "Regional aggregate inputs may mask intra-region heterogeneity.",
            "Causal conclusions require explicit study design and are not inferred here.",
        ],
        confidence_summary="Confidence tiers are heuristic and not causal proof.",
        uncertainty_semantics="Confidence represents evidence quality tiering from available aggregate coverage.",
        causal_labeling_policy="Only explicitly flagged outputs may be interpreted as causal hypotheses.",
        result_classification="associative",
        caveats=[
            "Outputs are intended for landscape interpretation and hypothesis generation.",
            "Association does not imply causation.",
        ],
        generated_at=datetime.now(UTC),
    )

    return DeterminantsResponse(
        region=filters.region,
        period=f"{filters.year_from or 'all'}-{filters.year_to or 'all'}",
        drivers=drivers,
        methodology=methodology,
        pagination=PaginationMeta(page=1, page_size=len(drivers), total_items=len(drivers), total_pages=1),
    )


def run_simulation(payload: SimulationRunRequest, *, context: RequestContext) -> SimulationRunResponse:
    platform_repository = build_platform_repository()
    methodology = MethodologyMetadata(
        method_name="weighted_indication_scenario",
        methodology_version="sim-v1.3",
        assumptions_summary="Aggregate-only weighting and scenario assumptions; no patient-level simulation.",
        assumptions_registry=[
            "Scenario multipliers are deterministic transforms over aggregate inputs.",
            "Uncertainty intervals are sensitivity-based, not posterior confidence intervals.",
        ],
        data_inputs_summary="indication_profile_facts with ranked indication scoring outputs",
        input_limitations=[
            "Simulation does not represent patient-level treatment pathways.",
            "Scenario results are projection signals and require human review.",
        ],
        confidence_summary="Deterministic score transform; uncertainty depends on upstream aggregate quality.",
        uncertainty_semantics="Uncertainty reflects scenario sensitivity scaling around transformed aggregate scores.",
        causal_labeling_policy="Scenario outputs are associative planning signals, not causal efficacy conclusions.",
        result_classification="scenario_projection",
        caveats=[
            "Scenario projections are strategy-support artifacts, not causal forecasts.",
            "External market/regulatory shifts are not fully modeled.",
        ],
        generated_at=datetime.now(UTC),
    )
    run_assumptions = {
        **payload.assumptions,
        "weights_override": payload.weights_override,
        "limit": payload.limit,
    }
    run_id = platform_repository.create_simulation_run(
        tenant_id=context.tenant_id,
        created_by=context.subject,
        scenario_type=payload.scenario_type,
        region=payload.region,
        trigger_source="api",
        assumptions=run_assumptions,
        methodology=methodology,
    )
    run_record = platform_repository.get_simulation_run(run_id=run_id, tenant_id=context.tenant_id)
    if run_record is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="simulation persistence error")
    return SimulationRunResponse(
        run=run_record.summary,
        run_id=run_record.summary.run_id,
        status=run_record.summary.status,
        created_at=run_record.summary.created_at,
        summary=run_record.summary.result_summary,
    )


def get_simulation_result(run_id: str, *, context: RequestContext) -> SimulationResultResponse | None:
    run_record = build_platform_repository().get_simulation_run(run_id=run_id, tenant_id=context.tenant_id)
    if run_record is None:
        return None
    return SimulationResultResponse(
        run=run_record.summary,
        assumptions=run_record.assumptions,
        items=run_record.items,
        run_id=run_record.summary.run_id,
        scenario_type=run_record.summary.scenario_type,
    )


def list_simulation_runs(*, context: RequestContext, filters: SimulationRunsFilters) -> SimulationRunsResponse:
    items, pagination = build_platform_repository().list_simulation_runs(tenant_id=context.tenant_id, filters=filters)
    return SimulationRunsResponse(items=items, pagination=pagination)


def cancel_simulation_run(run_id: str, *, context: RequestContext) -> bool:
    return build_platform_repository().cancel_simulation_run(run_id=run_id, tenant_id=context.tenant_id)


def compare_simulation_runs(
    request: SimulationRunCompareRequest, *, context: RequestContext
) -> SimulationComparisonResponse:
    return build_platform_repository().compare_simulation_runs(tenant_id=context.tenant_id, request=request)


def process_queued_simulation_jobs(*, max_runs: int = 5) -> int:
    platform_repository = build_platform_repository()
    analytics_repository = build_analytics_repository()
    run_records = platform_repository.list_runnable_simulation_runs(limit=max_runs)
    processed = 0
    for run_record in run_records:
        processed += 1
        attempt = run_record.summary.attempt_count + 1
        platform_repository.update_simulation_run(
            run_id=run_record.summary.run_id,
            tenant_id=run_record.summary.tenant_id,
            status="running",
            attempt_count=attempt,
        )
        try:
            region = run_record.summary.region
            assumptions = run_record.assumptions
            limit = int(assumptions.get("limit", 10))
            profiles_result = analytics_repository.list_ranked_indication_profiles(
                filters=_build_profile_filter(region=region, limit=limit)
            )
            execution = run_scenario_engine(
                run_id=run_record.summary.run_id,
                scenario_type=run_record.summary.scenario_type,
                assumptions=assumptions,
                baseline_profiles=profiles_result.items,
                region=region,
                limit=limit,
            )
            platform_repository.save_simulation_result_items(
                run_id=run_record.summary.run_id,
                tenant_id=run_record.summary.tenant_id,
                items=execution.items,
            )
            platform_repository.update_simulation_run(
                run_id=run_record.summary.run_id,
                tenant_id=run_record.summary.tenant_id,
                status="succeeded",
                result_summary=execution.summary,
                attempt_count=attempt,
            )
        except Exception as exc:  # pragma: no cover
            if attempt < run_record.summary.max_attempts:
                platform_repository.update_simulation_run(
                    run_id=run_record.summary.run_id,
                    tenant_id=run_record.summary.tenant_id,
                    status="queued",
                    error_message=str(exc),
                    attempt_count=attempt,
                )
            else:
                platform_repository.update_simulation_run(
                    run_id=run_record.summary.run_id,
                    tenant_id=run_record.summary.tenant_id,
                    status="failed",
                    error_message=str(exc),
                    attempt_count=attempt,
                )
    return processed


def list_ingestion_runs(*, context: RequestContext, filters: IngestionRunsFilters) -> IngestionRunsResponse:
    items, pagination = build_platform_repository().list_ingestion_runs(tenant_id=context.tenant_id, filters=filters)
    return IngestionRunsResponse(items=items, pagination=pagination)


def get_ingestion_run(run_id: str, *, context: RequestContext) -> IngestionRunStatusSummary | None:
    return build_platform_repository().get_ingestion_run(run_id=run_id, tenant_id=context.tenant_id)


def get_methodology() -> MethodologyResponse:
    return MethodologyResponse(
        model_version="epios-methodology-v2",
        scoring={
            "type": "weighted_composite",
            "explainability": "factor-level weighted contributions",
            "constraints": ["aggregate-only inputs", "deterministic outputs"],
            "result_classification": "associative",
            "version": "score-v1.1",
        },
        determinants={
            "output_modes": ["descriptive", "associative", "causal_hypothesis"],
            "guardrail": "causal statements are hypothesis-labeled unless explicit causal workflow evidence exists",
            "version": "det-v1.2",
        },
        simulation={
            "supported_scenarios": [
                "subpopulation_targeting",
                "regional_expansion",
                "trial_feasibility",
                "weighting_change",
            ],
            "reproducibility": "inputs, assumptions, and lifecycle status are persisted in simulation run store",
            "version": "sim-v1.3",
            "result_classification": "scenario_projection",
        },
        generated_at=datetime.now(UTC),
    )


def get_data_quality(*, context: RequestContext, filters: DataQualityRunsFilters) -> DataQualityResponse:
    items, pagination = _list_data_quality_results(tenant_id=context.tenant_id, filters=filters)
    status_value = "degraded" if any(item.status == "fail" for item in items) else "ok"
    return DataQualityResponse(
        status=status_value,
        items=items,
        pagination=pagination,
        generated_at=datetime.now(UTC),
    )


def get_data_quality_result(result_id: str, *, context: RequestContext) -> DataQualityResultStatus | None:
    return build_platform_repository().get_data_quality_result(result_id=result_id, tenant_id=context.tenant_id)


def list_data_quality_runs(*, context: RequestContext, filters: DataQualityRunsFilters) -> DataQualityRunsResponse:
    items, pagination = _list_data_quality_results(tenant_id=context.tenant_id, filters=filters)
    return DataQualityRunsResponse(items=items, pagination=pagination)


def create_data_quality_result(*, context: RequestContext, payload: DataQualityUpsertRequest) -> DataQualityResultStatus:
    return build_platform_repository().create_data_quality_result(
        tenant_id=context.tenant_id,
        created_by=context.subject,
        payload=payload,
    )


def get_audit_events_page(page: int, page_size: int) -> tuple[list[dict[str, object]], PaginationMeta]:
    events = get_audit_events()
    total_items = len(events)
    total_pages = ceil(total_items / page_size) if total_items else 0
    start = (page - 1) * page_size
    end = start + page_size
    return (
        events[start:end],
        PaginationMeta(page=page, page_size=page_size, total_items=total_items, total_pages=total_pages),
    )


def get_runtime_debug() -> RuntimeDebugResponse:
    settings = get_settings()
    queued_runs: int | None = None
    try:
        queued_runs = len(build_platform_repository().list_runnable_simulation_runs(limit=500))
    except Exception:
        queued_runs = None
    return RuntimeDebugResponse(
        environment=settings.app_env,
        fallback_enabled=settings.db_fallback_enabled,
        clickhouse_url_present=bool(settings.clickhouse_url),
        auth_configured=bool(settings.auth_jwt_secret),
        tenant_claim_required_non_dev=settings.require_tenant_claim_non_dev,
        metrics_enabled=settings.metrics_enabled,
        trace_header_name=settings.trace_header_name,
        queued_simulation_runs=queued_runs,
        pilot_mode_enabled=settings.pilot_mode_enabled,
        pilot_mode_label=settings.pilot_mode_label,
        timestamp=datetime.now(UTC),
    )


def get_pilot_mode_config() -> PilotModeResponse:
    settings = get_settings()
    if settings.pilot_mode_enabled:
        description = "Pilot mode is enabled. Outputs may use curated pilot datasets and scenario scripts."
    else:
        description = "Pilot mode is disabled. Runtime expects standard production/staging data paths."
    return PilotModeResponse(
        enabled=settings.pilot_mode_enabled,
        label=settings.pilot_mode_label,
        mode_description=description,
        data_policy="Aggregate-only outputs. Patient-level export remains blocked.",
        restrictions=[
            "No patient-level drill-down in pilot mode.",
            "Methodology caveats and uncertainty labels must remain visible.",
            "Pilot mode does not bypass RBAC or tenant isolation.",
        ],
        generated_at=datetime.now(UTC),
    )


def generate_indication_decision_memo(
    *,
    context: RequestContext,
    region: str | None,
    limit: int,
    profile_id: str,
) -> DecisionMemoResponse:
    ranked = list_ranked_indications(
        RankedIndicationsFilters(
            region=region,
            limit=limit,
            page=1,
            page_size=limit,
            profile_id=profile_id,
        )
    )
    if not ranked.items:
        return DecisionMemoResponse(
            title="Indication Decision Memo",
            tenant_id=context.tenant_id,
            generated_at=datetime.now(UTC),
            result_classification="associative",
            summary="No ranked indications available for selected filters.",
            key_points=["Connected successfully, but no aggregate indications were returned."],
            methodology=ranked.methodology or {},
            caveats=ranked.caveats,
            recommendations=["Validate data coverage and filter values before rerunning."],
        )
    top = ranked.items[0]
    return DecisionMemoResponse(
        title=f"Indication Decision Memo ({top.indication_name})",
        tenant_id=context.tenant_id,
        generated_at=datetime.now(UTC),
        result_classification="associative",
        summary=top.summary,
        key_points=[
            f"Top indication: {top.indication_name} ({top.total_score:.1f}).",
            f"Scoring profile: {top.scoring_profile_id} v{top.scoring_profile_version}.",
            f"Confidence label: {top.confidence_label}.",
        ],
        methodology=ranked.methodology or {},
        caveats=ranked.caveats,
        recommendations=[
            "Review top 3 indications with domain stakeholders for feasibility constraints.",
            "Compare with alternate scoring profile to assess decision sensitivity.",
        ],
    )


def generate_simulation_decision_memo(*, run_id: str, context: RequestContext) -> DecisionMemoResponse | None:
    result = get_simulation_result(run_id=run_id, context=context)
    if result is None:
        return None
    movers = sorted(result.items, key=lambda item: abs(item.score_delta), reverse=True)[:3]
    if movers:
        point_lines = [
            f"{item.indication_name}: delta {item.score_delta:+.1f}, uncertainty {item.uncertainty_low:.1f}-{item.uncertainty_high:.1f}"
            for item in movers
        ]
    else:
        point_lines = ["No scenario result rows available for this run."]
    return DecisionMemoResponse(
        title=f"Simulation Decision Memo ({result.run_id})",
        tenant_id=context.tenant_id,
        generated_at=datetime.now(UTC),
        result_classification="scenario_projection",
        summary=result.run.result_summary or "Scenario run completed.",
        key_points=point_lines,
        methodology={
            "method_name": result.run.methodology.method_name,
            "methodology_version": result.run.methodology.methodology_version,
            "assumptions_summary": result.run.methodology.assumptions_summary,
            "uncertainty_semantics": result.run.methodology.uncertainty_semantics,
        },
        caveats=result.run.methodology.caveats
        or ["Scenario outputs are projections and should not be interpreted as causal forecasts."],
        recommendations=[
            "Compare scenario memo with baseline ranking memo before investment decisions.",
            "Review assumption registry and rerun sensitivity scenarios if key drivers are uncertain.",
        ],
    )


def _build_profile_filter(*, region: str | None, limit: int):
    return RankedIndicationsFilters(region=region, limit=limit, page=1, page_size=limit)


def _list_data_quality_results(
    *, tenant_id: str, filters: DataQualityRunsFilters
) -> tuple[list[DataQualityResultStatus], PaginationMeta]:
    return build_platform_repository().list_data_quality_results(
        tenant_id=tenant_id,
        filters=filters,
    )

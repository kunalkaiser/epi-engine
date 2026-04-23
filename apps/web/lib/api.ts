import type {
  AppRole,
  AuditEventsResponse,
  AuthMeResponse,
  DataQualityResponse,
  DataQualityRunsResponse,
  DebugSnapshot,
  DeterminantsResponse,
  DiseasesResponse,
  HealthResponse,
  IngestionRunsResponse,
  MethodologyResponse,
  MortalityResponse,
  PaginationMeta,
  PrevalenceResponse,
  IncidenceResponse,
  RankedIndicationsResponse,
  ReadyResponse,
  RuntimeDebugResponse,
  PilotModeResponse,
  DecisionMemoResponse,
  SimulationComparisonResponse,
  SimulationResultResponse,
  SimulationRunResponse,
  SimulationRunsResponse,
  TopIndicationsResponse,
} from "./types";

const API_PROXY_BASE = "/api/backend";

type QueryValue = string | number | undefined;

type RegionTimeParams = {
  region?: string;
  yearFrom?: number;
  yearTo?: number;
  page?: number;
  pageSize?: number;
};

type TopIndicationsParams = RegionTimeParams & {
  limit?: number;
  profileId?: string;
};

type RankedIndicationsParams = RegionTimeParams & {
  limit?: number;
  profileId?: string;
  incidenceWeight?: number;
  prevalenceWeight?: number;
  unmetNeedWeight?: number;
  marketSizeWeight?: number;
  competitionPenaltyWeight?: number;
  equityScoreWeight?: number;
};

type SimulationRunPayload = {
  scenarioType: "subpopulation_targeting" | "regional_expansion" | "trial_feasibility" | "weighting_change";
  region?: string;
  limit?: number;
  assumptions?: Record<string, unknown>;
  weightsOverride?: Record<string, number>;
};

type DataQualityCreatePayload = {
  domain: string;
  checkType: string;
  severity: "low" | "medium" | "high" | "critical";
  status: "pass" | "warn" | "fail";
  summaryMetrics?: Record<string, unknown>;
  failingDimensions?: string[];
  thresholds?: Record<string, unknown>;
  rulesVersion: string;
  ingestionRunId?: string;
  measuredAt: string;
};

export type ApiState<T> =
  | { status: "loading"; data: null; error: null }
  | { status: "success"; data: T; error: null }
  | { status: "empty"; data: T | null; error: null }
  | { status: "error"; data: null; error: string };

export async function fetchDebugSnapshot(): Promise<DebugSnapshot> {
  const response = await fetch("/api/debug", { cache: "no-store", headers: { Accept: "application/json" } });
  if (!response.ok) {
    throw new Error(`Debug endpoint failed with status ${response.status}`);
  }
  return (await response.json()) as DebugSnapshot;
}

export async function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("GET", "/health", {});
}

export async function fetchReady(): Promise<ReadyResponse> {
  const response = await request<any>("GET", "/ready", {});
  return {
    status: response.status,
    dependencies: Array.isArray(response.dependencies)
      ? response.dependencies.map((item: any) => ({
          name: item.name,
          status: item.status,
          detail: item.detail,
        }))
      : [],
    timestamp: response.timestamp,
  };
}

export async function fetchRuntimeDebug(): Promise<RuntimeDebugResponse> {
  const response = await request<any>("GET", "/debug/runtime", {});
  return {
    environment: response.environment,
    fallbackEnabled: response.fallback_enabled,
    clickhouseUrlPresent: response.clickhouse_url_present,
    authConfigured: response.auth_configured,
    tenantClaimRequiredNonDev: response.tenant_claim_required_non_dev,
    metricsEnabled: response.metrics_enabled,
    traceHeaderName: response.trace_header_name,
    queuedSimulationRuns: response.queued_simulation_runs ?? null,
    pilotModeEnabled: response.pilot_mode_enabled,
    pilotModeLabel: response.pilot_mode_label,
    timestamp: response.timestamp,
  };
}

export async function fetchPilotModeConfig(): Promise<PilotModeResponse> {
  const response = await request<any>("GET", "/pilot/config", {});
  return {
    enabled: response.enabled,
    label: response.label,
    modeDescription: response.mode_description,
    dataPolicy: response.data_policy,
    restrictions: response.restrictions ?? [],
    generatedAt: response.generated_at,
  };
}

export async function fetchAuthMe(): Promise<AuthMeResponse> {
  const response = await request<any>("GET", "/auth/me", {});
  return {
    subject: response.subject,
    role: response.role,
    tenantId: response.tenant_id,
    issuer: response.issuer,
    audience: response.audience,
    expiresAt: response.expires_at ?? null,
  };
}

export async function fetchDiseases(page = 1, pageSize = 10): Promise<DiseasesResponse> {
  const response = await request<any>("GET", "/diseases", { page, page_size: pageSize });
  return {
    items: response.items.map((item: any) => ({
      diseaseId: item.disease_id,
      diseaseName: item.disease_name,
      regions: item.regions,
      yearMin: item.year_min,
      yearMax: item.year_max,
    })),
    pagination: normalizePagination(response.pagination),
  };
}

export async function fetchIncidence(params: RegionTimeParams): Promise<IncidenceResponse> {
  const response = await request<any>("GET", "/incidence", mapRegionTimeParams(params));
  return {
    items: response.items.map((item: any) => ({
      diseaseId: item.disease_id,
      diseaseName: item.disease_name,
      regionCode: item.region_code,
      year: item.year,
      incidentCases: item.incident_cases,
      population: item.population,
      incidencePer100k: item.incidence_per_100k,
    })),
    pagination: normalizePagination(response.pagination),
  };
}

export async function fetchPrevalence(params: RegionTimeParams): Promise<PrevalenceResponse> {
  const response = await request<any>("GET", "/prevalence", mapRegionTimeParams(params));
  return {
    items: response.items.map((item: any) => ({
      diseaseId: item.disease_id,
      diseaseName: item.disease_name,
      regionCode: item.region_code,
      year: item.year,
      prevalentCases: item.prevalent_cases,
      population: item.population,
      prevalencePer100k: item.prevalence_per_100k,
    })),
    pagination: normalizePagination(response.pagination),
  };
}

export async function fetchMortality(params: RegionTimeParams): Promise<MortalityResponse> {
  const response = await request<any>("GET", "/mortality", mapRegionTimeParams(params));
  return {
    items: response.items.map((item: any) => ({
      diseaseId: item.disease_id,
      diseaseName: item.disease_name,
      regionCode: item.region_code,
      year: item.year,
      deaths: item.deaths,
      population: item.population,
      mortalityPer100k: item.mortality_per_100k,
    })),
    pagination: normalizePagination(response.pagination),
  };
}

export async function fetchDeterminants(params: RegionTimeParams): Promise<DeterminantsResponse> {
  const response = await request<any>("GET", "/determinants", mapRegionTimeParams(params));
  return {
    diseaseId: response.disease_id,
    region: response.region,
    period: response.period,
    drivers: response.drivers.map((driver: any) => ({
      factor: driver.factor,
      category: driver.category,
      relationshipType: driver.relationship_type,
      resultClassification: driver.result_classification,
      contributionScore: driver.contribution_score,
      confidence: driver.confidence,
      uncertaintyNote: driver.uncertainty_note,
    })),
    methodology: {
      methodName: response.methodology.method_name,
      methodologyVersion: response.methodology.methodology_version,
      assumptionsSummary: response.methodology.assumptions_summary,
      assumptionsRegistry: response.methodology.assumptions_registry,
      dataInputsSummary: response.methodology.data_inputs_summary,
      inputLimitations: response.methodology.input_limitations,
      confidenceSummary: response.methodology.confidence_summary,
      uncertaintySemantics: response.methodology.uncertainty_semantics,
      causalLabelingPolicy: response.methodology.causal_labeling_policy,
      resultClassification: response.methodology.result_classification,
      caveats: response.methodology.caveats,
      generatedAt: response.methodology.generated_at,
    },
    pagination: normalizePagination(response.pagination),
  };
}

export async function fetchTopIndications(params: TopIndicationsParams): Promise<TopIndicationsResponse> {
  const response = await request<any>("GET", "/indications/top", {
    ...mapRegionTimeParams(params),
    limit: params.limit,
    profile_id: params.profileId,
  });
  return {
    items: response.items.map((item: any) => ({
      indicationId: item.indication_id,
      indicationName: item.indication_name,
      incidenceScore: item.incidence_score,
      unmetNeedScore: item.unmet_need_score,
      marketSizeScore: item.market_size_score,
      competitionScore: item.competition_score,
      totalScore: item.total_score,
    })),
    pagination: normalizePagination(response.pagination),
    scoringProfile: response.scoring_profile ?? null,
    methodology: response.methodology ?? null,
  };
}

export async function fetchRankedIndications(params: RankedIndicationsParams): Promise<RankedIndicationsResponse> {
  const response = await request<any>("GET", "/indications/ranked", {
    ...mapRegionTimeParams(params),
    limit: params.limit,
    profile_id: params.profileId,
    incidence_weight: params.incidenceWeight,
    prevalence_weight: params.prevalenceWeight,
    unmet_need_weight: params.unmetNeedWeight,
    market_size_weight: params.marketSizeWeight,
    competition_penalty_weight: params.competitionPenaltyWeight,
    equity_score_weight: params.equityScoreWeight,
  });
  return {
    items: response.items.map((item: any) => ({
      indicationId: item.indication_id,
      indicationName: item.indication_name,
      regionCode: item.region_code,
      totalScore: item.total_score,
      summary: item.summary,
      scoringProfileId: item.scoring_profile_id,
      scoringProfileVersion: item.scoring_profile_version,
      methodologyVersion: item.methodology_version,
      confidenceLabel: item.confidence_label,
      resultClassification: item.result_classification,
      inputProvenanceSummary: item.input_provenance_summary,
      dataLimitations: item.data_limitations,
      explanations: item.explanations.map((exp: any) => ({
        factor: exp.factor,
        rawValue: exp.raw_value,
        adjustedScore: exp.adjusted_score,
        weight: exp.weight,
        weightedContribution: exp.weighted_contribution,
        explanation: exp.explanation,
        evidenceClassification: exp.evidence_classification,
        caveat: exp.caveat,
      })),
    })),
    pagination: normalizePagination(response.pagination),
    scoringProfile: response.scoring_profile ?? null,
    methodology: response.methodology ?? null,
    caveats: response.caveats ?? [],
  };
}

export async function createSimulationRun(payload: SimulationRunPayload): Promise<SimulationRunResponse> {
  const response = await request<any>("POST", "/simulation/run", {}, {
    scenario_type: payload.scenarioType,
    region: payload.region,
    limit: payload.limit ?? 10,
    assumptions: payload.assumptions ?? {},
    weights_override: payload.weightsOverride ?? {},
  });
  return mapSimulationRunResponse(response);
}

export async function fetchSimulationRuns(params?: { status?: string; scenarioType?: string; page?: number; pageSize?: number }): Promise<SimulationRunsResponse> {
  const response = await request<any>("GET", "/simulation/runs", {
    status: params?.status,
    scenario_type: params?.scenarioType,
    page: params?.page ?? 1,
    page_size: params?.pageSize ?? 20,
  });
  return {
    items: response.items.map(mapSimulationRunSummary),
    pagination: normalizePagination(response.pagination),
  };
}

export async function fetchSimulationResult(runId: string): Promise<SimulationResultResponse> {
  const response = await request<any>("GET", `/simulation/results/${encodeURIComponent(runId)}`, {});
  return {
    run: mapSimulationRunSummary(response.run),
    assumptions: response.assumptions,
    items: response.items.map((item: any) => ({
      indicationId: item.indication_id,
      indicationName: item.indication_name,
      baselineScore: item.baseline_score,
      simulatedScore: item.simulated_score,
      scoreDelta: item.score_delta,
      uncertaintyLow: item.uncertainty_low,
      uncertaintyHigh: item.uncertainty_high,
      outcomeDrivers: item.outcome_drivers,
      scoreInputs: item.score_inputs,
      traceId: item.trace_id,
      resultClassification: item.result_classification,
      caveats: item.caveats ?? [],
    })),
    runId: response.run_id,
    scenarioType: response.scenario_type,
  };
}

export async function cancelSimulationRun(runId: string): Promise<{ runId: string; status: string }> {
  const response = await request<any>("POST", `/simulation/runs/${encodeURIComponent(runId)}/cancel`, {});
  return {
    runId: response.run_id,
    status: response.status,
  };
}

export async function compareSimulationRuns(runIds: string[]): Promise<SimulationComparisonResponse> {
  const response = await request<any>("POST", "/simulation/compare", {}, { run_ids: runIds });
  return {
    tenantId: response.tenant_id,
    comparedRunIds: response.compared_run_ids,
    assumptionDeltas: response.assumption_deltas,
    scoreDeltas: response.score_deltas.map((item: any) => ({
      indicationId: item.indication_id,
      indicationName: item.indication_name,
      minScore: item.min_score,
      maxScore: item.max_score,
      scoreSpread: item.score_spread,
      runScores: item.run_scores,
    })),
    generatedAt: response.generated_at,
  };
}

export async function fetchDataQuality(params?: { domain?: string; status?: string; severity?: string; page?: number; pageSize?: number }): Promise<DataQualityResponse> {
  const response = await request<any>("GET", "/data-quality", {
    domain: params?.domain,
    status: params?.status,
    severity: params?.severity,
    page: params?.page ?? 1,
    page_size: params?.pageSize ?? 20,
  });
  return {
    status: response.status,
    items: response.items.map(mapDataQualityItem),
    pagination: normalizePagination(response.pagination),
    generatedAt: response.generated_at,
  };
}

export async function fetchAdminDataQualityRuns(params?: { domain?: string; status?: string; severity?: string; page?: number; pageSize?: number }): Promise<DataQualityRunsResponse> {
  const response = await request<any>("GET", "/admin/data-quality-runs", {
    domain: params?.domain,
    status: params?.status,
    severity: params?.severity,
    page: params?.page ?? 1,
    page_size: params?.pageSize ?? 20,
  });
  return {
    items: response.items.map(mapDataQualityItem),
    pagination: normalizePagination(response.pagination),
  };
}

export async function createAdminDataQualityRun(payload: DataQualityCreatePayload) {
  const response = await request<any>("POST", "/admin/data-quality-runs", {}, {
    domain: payload.domain,
    check_type: payload.checkType,
    severity: payload.severity,
    status: payload.status,
    summary_metrics: payload.summaryMetrics ?? {},
    failing_dimensions: payload.failingDimensions ?? [],
    thresholds: payload.thresholds ?? {},
    rules_version: payload.rulesVersion,
    ingestion_run_id: payload.ingestionRunId,
    measured_at: payload.measuredAt,
  });
  return mapDataQualityItem(response);
}

export async function fetchIngestionRuns(params?: {
  sourceSystem?: string;
  status?: string;
  triggerSource?: string;
  page?: number;
  pageSize?: number;
  dateFrom?: string;
  dateTo?: string;
}): Promise<IngestionRunsResponse> {
  const response = await request<any>("GET", "/admin/ingestion-runs", {
    source_system: params?.sourceSystem,
    status: params?.status,
    trigger_source: params?.triggerSource,
    page: params?.page ?? 1,
    page_size: params?.pageSize ?? 20,
    date_from: params?.dateFrom,
    date_to: params?.dateTo,
  });
  return {
    items: response.items.map((item: any) => ({
      runId: item.run_id,
      tenantId: item.tenant_id,
      datasetName: item.dataset_name,
      sourceSystem: item.source_system,
      triggerSource: item.trigger_source,
      status: item.status,
      recordsProcessed: item.records_processed,
      recordsInserted: item.records_inserted,
      recordsUpdated: item.records_updated,
      recordsRejected: item.records_rejected,
      validationSummary: item.validation_summary,
      errorSummary: item.error_summary,
      freshnessMetric: item.freshness_metric,
      provenanceRef: item.provenance_ref,
      artifactRef: item.artifact_ref,
      createdBy: item.created_by,
      startedAt: item.started_at,
      completedAt: item.completed_at,
      createdAt: item.created_at,
      updatedAt: item.updated_at,
    })),
    pagination: normalizePagination(response.pagination),
  };
}

export async function fetchAuditEvents(params?: { page?: number; pageSize?: number }): Promise<AuditEventsResponse> {
  const response = await request<any>("GET", "/audit/events", {
    page: params?.page ?? 1,
    page_size: params?.pageSize ?? 20,
  });
  return {
    items: response.items,
    pagination: normalizePagination(response.pagination),
  };
}

export async function fetchMethodology(): Promise<MethodologyResponse> {
  const response = await request<any>("GET", "/methodology", {});
  return {
    modelVersion: response.model_version,
    scoring: response.scoring,
    determinants: response.determinants,
    simulation: response.simulation,
    generatedAt: response.generated_at,
  };
}

export async function fetchIndicationDecisionMemo(params?: {
  region?: string;
  limit?: number;
  profileId?: string;
}): Promise<DecisionMemoResponse> {
  const response = await request<any>("GET", "/reports/decision-memo", {
    region: params?.region,
    limit: params?.limit ?? 5,
    profile_id: params?.profileId ?? "default_v1",
  });
  return mapDecisionMemo(response);
}

export async function fetchSimulationDecisionMemo(runId: string): Promise<DecisionMemoResponse> {
  const response = await request<any>("GET", `/reports/simulation/${encodeURIComponent(runId)}/decision-memo`, {});
  return mapDecisionMemo(response);
}

export function getRoleFromDebugSnapshot(snapshot: DebugSnapshot | null): AppRole | "unknown" {
  const role = snapshot?.auth.role;
  return isKnownRole(role) ? role : "unknown";
}

export function isEmptyResponse(response: { items: unknown[]; pagination: PaginationMeta }): boolean {
  return response.items.length === 0 || response.pagination.totalItems === 0;
}

async function request<T>(
  method: "GET" | "POST",
  path: string,
  query: Record<string, QueryValue>,
  body?: unknown,
): Promise<T> {
  const queryParams = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== "") {
      queryParams.set(key, String(value));
    }
  }
  const queryString = queryParams.toString();
  const url = `${API_PROXY_BASE}${path.startsWith("/") ? path : `/${path}`}${queryString ? `?${queryString}` : ""}`;

  const response = await fetch(url, {
    method,
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "X-Request-ID": createRequestId(),
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const fallback = `Request failed with status ${response.status}`;
    try {
      const payload = (await response.json()) as { error?: { message?: string }; detail?: string };
      if (payload.error?.message) {
        throw new Error(normalizeApiError(payload.error.message));
      }
      if (payload.detail) {
        throw new Error(normalizeApiError(payload.detail));
      }
      throw new Error(fallback);
    } catch (error) {
      if (error instanceof Error && error.message !== fallback) {
        throw error;
      }
      throw new Error(fallback);
    }
  }

  if (response.status === 204) {
    return {} as T;
  }
  return (await response.json()) as T;
}

function createRequestId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `req-${Date.now()}-${Math.floor(Math.random() * 1_000_000)}`;
}

function mapRegionTimeParams(params: RegionTimeParams): Record<string, QueryValue> {
  return {
    region: params.region,
    year_from: params.yearFrom,
    year_to: params.yearTo,
    page: params.page,
    page_size: params.pageSize,
  };
}

function mapSimulationRunResponse(run: any): SimulationRunResponse {
  return {
    run: mapSimulationRunSummary(run.run),
    runId: run.run_id,
    status: run.status,
    createdAt: run.created_at,
    summary: run.summary,
  };
}

function mapSimulationRunSummary(run: any) {
  return {
    runId: run.run_id,
    tenantId: run.tenant_id,
    status: run.status,
    scenarioType: run.scenario_type,
    region: run.region,
    createdBy: run.created_by,
    triggerSource: run.trigger_source,
    resultSummary: run.result_summary,
    artifactRef: run.artifact_ref,
    errorMessage: run.error_message,
    methodology: {
      methodName: run.methodology.method_name,
      methodologyVersion: run.methodology.methodology_version,
      assumptionsSummary: run.methodology.assumptions_summary,
      assumptionsRegistry: run.methodology.assumptions_registry,
      dataInputsSummary: run.methodology.data_inputs_summary,
      inputLimitations: run.methodology.input_limitations,
      confidenceSummary: run.methodology.confidence_summary,
      uncertaintySemantics: run.methodology.uncertainty_semantics,
      causalLabelingPolicy: run.methodology.causal_labeling_policy,
      resultClassification: run.methodology.result_classification,
      caveats: run.methodology.caveats,
      generatedAt: run.methodology.generated_at,
    },
    createdAt: run.created_at,
    updatedAt: run.updated_at,
    attemptCount: run.attempt_count ?? 0,
    maxAttempts: run.max_attempts ?? 2,
  };
}

function mapDataQualityItem(item: any) {
  return {
    resultId: item.result_id,
    tenantId: item.tenant_id,
    domain: item.domain,
    checkType: item.check_type,
    severity: item.severity,
    status: item.status,
    summaryMetrics: item.summary_metrics,
    failingDimensions: item.failing_dimensions,
    thresholds: item.thresholds,
    rulesVersion: item.rules_version,
    ingestionRunId: item.ingestion_run_id,
    measuredAt: item.measured_at,
    createdBy: item.created_by,
    createdAt: item.created_at,
    updatedAt: item.updated_at,
  };
}

function normalizePagination(pagination: { page: number; page_size: number; total_items: number; total_pages: number }): PaginationMeta {
  return {
    page: pagination.page,
    pageSize: pagination.page_size,
    totalItems: pagination.total_items,
    totalPages: pagination.total_pages,
  };
}

function normalizeApiError(message: string): string {
  if (message.includes("missing Authorization header")) {
    return "Backend authorization is missing. Configure API_AUTH_TOKEN on the web server runtime.";
  }
  if (message.includes("tenant_id is required")) {
    return "Tenant claim is missing in auth token.";
  }
  return message;
}

function mapDecisionMemo(response: any): DecisionMemoResponse {
  return {
    title: response.title,
    tenantId: response.tenant_id,
    generatedAt: response.generated_at,
    resultClassification: response.result_classification,
    summary: response.summary,
    keyPoints: response.key_points ?? [],
    methodology: response.methodology ?? {},
    caveats: response.caveats ?? [],
    recommendations: response.recommendations ?? [],
  };
}

function isKnownRole(role: string | undefined): role is AppRole {
  return (
    role === "admin" ||
    role === "analyst" ||
    role === "read_only" ||
    role === "auditor" ||
    role === "operations" ||
    role === "payer_aggregate_only" ||
    role === "trial_coordinator" ||
    role === "read_only_gov"
  );
}

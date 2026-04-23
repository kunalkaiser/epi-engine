export type PaginationMeta = {
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
};

export type AppRole =
  | "admin"
  | "analyst"
  | "read_only"
  | "auditor"
  | "operations"
  | "payer_aggregate_only"
  | "trial_coordinator"
  | "read_only_gov";

export type DiseaseListItem = {
  diseaseId: string;
  diseaseName: string;
  regions: string[];
  yearMin: number;
  yearMax: number;
};

export type DiseasesResponse = {
  items: DiseaseListItem[];
  pagination: PaginationMeta;
};

export type IncidenceAggregate = {
  diseaseId: string;
  diseaseName: string;
  regionCode: string;
  year: number;
  incidentCases: number;
  population: number;
  incidencePer100k: number;
};

export type PrevalenceAggregate = {
  diseaseId: string;
  diseaseName: string;
  regionCode: string;
  year: number;
  prevalentCases: number;
  population: number;
  prevalencePer100k: number;
};

export type MortalityAggregate = {
  diseaseId: string;
  diseaseName: string;
  regionCode: string;
  year: number;
  deaths: number;
  population: number;
  mortalityPer100k: number;
};

export type IncidenceResponse = {
  items: IncidenceAggregate[];
  pagination: PaginationMeta;
};

export type PrevalenceResponse = {
  items: PrevalenceAggregate[];
  pagination: PaginationMeta;
};

export type MortalityResponse = {
  items: MortalityAggregate[];
  pagination: PaginationMeta;
};

export type IndicationScore = {
  indicationId: string;
  indicationName: string;
  incidenceScore: number;
  unmetNeedScore: number;
  marketSizeScore: number;
  competitionScore: number;
  totalScore: number;
};

export type TopIndicationsResponse = {
  items: IndicationScore[];
  pagination: PaginationMeta;
  scoringProfile?: Record<string, unknown> | null;
  methodology?: Record<string, unknown> | null;
};

export type FactorExplanation = {
  factor: string;
  rawValue: number;
  adjustedScore: number;
  weight: number;
  weightedContribution: number;
  explanation: string;
  evidenceClassification?: "descriptive" | "associative" | "causal_hypothesis" | "scenario_projection";
  caveat?: string;
};

export type RankedIndication = {
  indicationId: string;
  indicationName: string;
  regionCode: string;
  totalScore: number;
  summary: string;
  explanations: FactorExplanation[];
  scoringProfileId?: string;
  scoringProfileVersion?: string;
  methodologyVersion?: string;
  confidenceLabel?: "low" | "medium" | "high";
  resultClassification?: "descriptive" | "associative" | "causal_hypothesis" | "scenario_projection";
  inputProvenanceSummary?: string;
  dataLimitations?: string[];
};

export type RankedIndicationsResponse = {
  items: RankedIndication[];
  pagination: PaginationMeta;
  scoringProfile?: Record<string, unknown> | null;
  methodology?: Record<string, unknown> | null;
  caveats?: string[];
};

export type MethodologyMetadata = {
  methodName: string;
  methodologyVersion: string;
  assumptionsSummary: string;
  assumptionsRegistry?: string[];
  dataInputsSummary: string;
  inputLimitations?: string[];
  confidenceSummary: string;
  uncertaintySemantics?: string;
  causalLabelingPolicy: string;
  resultClassification?: "descriptive" | "associative" | "causal_hypothesis" | "scenario_projection";
  caveats?: string[];
  generatedAt: string;
};

export type DeterminantDriver = {
  factor: string;
  category: "clinical" | "biomarker" | "social" | "environmental";
  relationshipType: "descriptive" | "associative" | "causal_hypothesis";
  resultClassification?: "descriptive" | "associative" | "causal_hypothesis";
  contributionScore: number;
  confidence: "low" | "medium" | "high";
  uncertaintyNote: string;
};

export type DeterminantsResponse = {
  diseaseId?: string | null;
  region?: string | null;
  period: string;
  drivers: DeterminantDriver[];
  methodology: MethodologyMetadata;
  pagination: PaginationMeta;
};

export type SimulationRunStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled";

export type SimulationResultItem = {
  indicationId: string;
  indicationName: string;
  baselineScore: number;
  simulatedScore: number;
  scoreDelta: number;
  uncertaintyLow: number;
  uncertaintyHigh: number;
  outcomeDrivers: string[];
  scoreInputs: Record<string, number>;
  traceId: string;
  resultClassification?: "scenario_projection";
  caveats?: string[];
};

export type SimulationRunSummary = {
  runId: string;
  tenantId: string;
  status: SimulationRunStatus;
  scenarioType: string;
  region?: string | null;
  createdBy: string;
  triggerSource: string;
  resultSummary?: string | null;
  artifactRef?: string | null;
  errorMessage?: string | null;
  methodology: MethodologyMetadata;
  createdAt: string;
  updatedAt: string;
  attemptCount: number;
  maxAttempts: number;
};

export type SimulationRunResponse = {
  run: SimulationRunSummary;
  runId: string;
  status: SimulationRunStatus;
  createdAt: string;
  summary?: string | null;
};

export type SimulationResultResponse = {
  run: SimulationRunSummary;
  assumptions: Record<string, unknown>;
  items: SimulationResultItem[];
  runId: string;
  scenarioType: string;
};

export type SimulationRunsResponse = {
  items: SimulationRunSummary[];
  pagination: PaginationMeta;
};

export type SimulationDeltaItem = {
  indicationId: string;
  indicationName: string;
  minScore: number;
  maxScore: number;
  scoreSpread: number;
  runScores: Record<string, number>;
};

export type SimulationComparisonResponse = {
  tenantId: string;
  comparedRunIds: string[];
  assumptionDeltas: Record<string, string[]>;
  scoreDeltas: SimulationDeltaItem[];
  generatedAt: string;
};

export type DataQualityResultStatus = {
  resultId: string;
  tenantId: string;
  domain: string;
  checkType: string;
  severity: "low" | "medium" | "high" | "critical";
  status: "pass" | "warn" | "fail";
  summaryMetrics: Record<string, unknown>;
  failingDimensions: string[];
  thresholds: Record<string, unknown>;
  rulesVersion: string;
  ingestionRunId?: string | null;
  measuredAt: string;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
};

export type DataQualityResponse = {
  status: "ok" | "degraded";
  items: DataQualityResultStatus[];
  pagination: PaginationMeta;
  generatedAt: string;
};

export type DataQualityRunsResponse = {
  items: DataQualityResultStatus[];
  pagination: PaginationMeta;
};

export type IngestionRunStatusSummary = {
  runId: string;
  tenantId: string;
  datasetName: string;
  sourceSystem: string;
  triggerSource: "scheduled" | "manual" | "backfill";
  status: "queued" | "running" | "succeeded" | "failed" | "cancelled";
  recordsProcessed: number;
  recordsInserted: number;
  recordsUpdated: number;
  recordsRejected: number;
  validationSummary: Record<string, unknown>;
  errorSummary: Record<string, unknown>;
  freshnessMetric?: string | null;
  provenanceRef?: string | null;
  artifactRef?: string | null;
  createdBy: string;
  startedAt: string;
  completedAt?: string | null;
  createdAt: string;
  updatedAt: string;
};

export type IngestionRunsResponse = {
  items: IngestionRunStatusSummary[];
  pagination: PaginationMeta;
};

export type AuthMeResponse = {
  subject: string;
  role: AppRole;
  tenantId: string;
  issuer?: string;
  audience?: string;
  expiresAt?: number | null;
};

export type MethodologyResponse = {
  modelVersion: string;
  scoring: Record<string, unknown>;
  determinants: Record<string, unknown>;
  simulation: Record<string, unknown>;
  generatedAt: string;
};

export type AuditEventItem = {
  event_name: string;
  payload: Record<string, unknown>;
};

export type AuditEventsResponse = {
  items: AuditEventItem[];
  pagination: PaginationMeta;
};

export type RuntimeDebugResponse = {
  environment: string;
  fallbackEnabled: boolean;
  clickhouseUrlPresent: boolean;
  authConfigured: boolean;
  tenantClaimRequiredNonDev: boolean;
  metricsEnabled: boolean;
  traceHeaderName: string;
  queuedSimulationRuns?: number | null;
  pilotModeEnabled?: boolean;
  pilotModeLabel?: string;
  timestamp: string;
};

export type PilotModeResponse = {
  enabled: boolean;
  label: string;
  modeDescription: string;
  dataPolicy: string;
  restrictions: string[];
  generatedAt: string;
};

export type DecisionMemoResponse = {
  title: string;
  tenantId: string;
  generatedAt: string;
  resultClassification: "descriptive" | "associative" | "causal_hypothesis" | "scenario_projection";
  summary: string;
  keyPoints: string[];
  methodology: Record<string, unknown>;
  caveats: string[];
  recommendations: string[];
};

export type HealthResponse = {
  status: string;
  environment: string;
  service: string;
  timestamp: string;
};

export type ReadyResponse = {
  status: "ok" | "degraded";
  dependencies: Array<{ name: string; status: "ok" | "degraded"; detail: string }>;
  timestamp: string;
};

export type DebugStatusState = "checking" | "ok" | "error";

export type DebugStatusItem = {
  status: DebugStatusState;
  detail: string;
};

export type DebugSnapshot = {
  frontend: DebugStatusItem;
  backend: DebugStatusItem & {
    baseUrl: string;
    baseUrlSource: "API_BASE_URL" | "BACKEND_URL" | "API_URL" | "NEXT_PUBLIC_API_BASE_URL" | "default";
    baseUrlConfigured: boolean;
  };
  auth: DebugStatusItem & {
    role: AppRole | "unknown";
    tokenSource: "forwarded_header" | "env_token" | "none";
    attached: boolean;
  };
  endpoints: {
    catalog: DebugStatusItem;
    incidence: DebugStatusItem;
    indications: DebugStatusItem;
  };
};

import type {
  DiseasesResponse,
  HealthResponse,
  IncidenceResponse,
  PaginationMeta,
  PrevalenceResponse,
  TopIndicationsResponse,
} from "./types";

const API_BASE_URL = getApiBaseUrl();
const API_AUTH_TOKEN = getApiAuthToken();
const CLIENT_ROLE = getClientRole(API_AUTH_TOKEN);

type QueryValue = string | number | undefined;
type RequestOptions = {
  withAuth?: boolean;
};

type RegionTimeParams = {
  region?: string;
  yearFrom?: number;
  yearTo?: number;
  page?: number;
  pageSize?: number;
};

type TopIndicationsParams = RegionTimeParams & {
  limit?: number;
};

export type AppRole = "admin" | "analyst" | "payer_aggregate_only" | "trial_coordinator" | "read_only_gov";

export type ApiState<T> =
  | { status: "loading"; data: null; error: null }
  | { status: "success"; data: T; error: null }
  | { status: "empty"; data: T; error: null }
  | { status: "error"; data: null; error: string };

export async function fetchDiseases(page = 1, pageSize = 10): Promise<DiseasesResponse> {
  const response = await request<{
    items: {
      disease_id: string;
      disease_name: string;
      regions: string[];
      year_min: number;
      year_max: number;
    }[];
    pagination: {
      page: number;
      page_size: number;
      total_items: number;
      total_pages: number;
    };
  }>("/diseases", { page, page_size: pageSize });

  return {
    items: response.items.map((item) => ({
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
  const response = await request<{
    items: {
      disease_id: string;
      disease_name: string;
      region_code: string;
      year: number;
      incident_cases: number;
      population: number;
      incidence_per_100k: number;
    }[];
    pagination: {
      page: number;
      page_size: number;
      total_items: number;
      total_pages: number;
    };
  }>("/incidence", mapRegionTimeParams(params));

  return {
    items: response.items.map((item) => ({
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
  const response = await request<{
    items: {
      disease_id: string;
      disease_name: string;
      region_code: string;
      year: number;
      prevalent_cases: number;
      population: number;
      prevalence_per_100k: number;
    }[];
    pagination: {
      page: number;
      page_size: number;
      total_items: number;
      total_pages: number;
    };
  }>("/prevalence", mapRegionTimeParams(params));

  return {
    items: response.items.map((item) => ({
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

export async function fetchTopIndications(params: TopIndicationsParams): Promise<TopIndicationsResponse> {
  const response = await request<{
    items: {
      indication_id: string;
      indication_name: string;
      incidence_score: number;
      unmet_need_score: number;
      market_size_score: number;
      competition_score: number;
      total_score: number;
    }[];
    pagination: {
      page: number;
      page_size: number;
      total_items: number;
      total_pages: number;
    };
  }>("/indications/top", {
    ...mapRegionTimeParams(params),
    limit: params.limit,
  });

  return {
    items: response.items.map((item) => ({
      indicationId: item.indication_id,
      indicationName: item.indication_name,
      incidenceScore: item.incidence_score,
      unmetNeedScore: item.unmet_need_score,
      marketSizeScore: item.market_size_score,
      competitionScore: item.competition_score,
      totalScore: item.total_score,
    })),
    pagination: normalizePagination(response.pagination),
  };
}

export async function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health", {}, { withAuth: false });
}

export function getEffectiveClientRole(): AppRole | "unknown" {
  return CLIENT_ROLE;
}

export function isEmptyResponse(response: { items: unknown[]; pagination: PaginationMeta }): boolean {
  return response.items.length === 0 || response.pagination.totalItems === 0;
}

async function request<T>(path: string, query: Record<string, QueryValue>, options?: RequestOptions): Promise<T> {
  const url = new URL(path, API_BASE_URL);
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== "") {
      url.searchParams.set(key, String(value));
    }
  }

  const response = await fetch(url.toString(), {
    cache: "no-store",
    headers: buildHeaders(options?.withAuth ?? true),
  });

  if (!response.ok) {
    const fallback = `Request failed with status ${response.status}`;
    try {
      const body = (await response.json()) as {
        error?: { message?: string };
        detail?: { msg?: string }[] | string;
      };
      if (body.error?.message) {
        throw new Error(body.error.message);
      }
      if (typeof body.detail === "string") {
        throw new Error(body.detail);
      }
      if (Array.isArray(body.detail) && body.detail[0]?.msg) {
        throw new Error(body.detail[0].msg);
      }
      throw new Error(fallback);
    } catch (error) {
      if (error instanceof Error && error.message !== fallback) {
        throw error;
      }
      throw new Error(fallback);
    }
  }

  return (await response.json()) as T;
}

function buildHeaders(withAuth: boolean): HeadersInit {
  const headers: Record<string, string> = {
    Accept: "application/json",
  };

  if (withAuth && API_AUTH_TOKEN) {
    headers.Authorization = `Bearer ${API_AUTH_TOKEN}`;
  }

  return headers;
}

function getApiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  return configured && configured.length > 0 ? configured : "http://localhost:8000";
}

function getApiAuthToken(): string {
  const configured = process.env.NEXT_PUBLIC_API_AUTH_TOKEN?.trim();
  return configured && configured.length > 0 ? configured : "";
}

function getClientRole(token: string): AppRole | "unknown" {
  const explicitRole = process.env.NEXT_PUBLIC_APP_ROLE?.trim();
  if (isKnownRole(explicitRole)) {
    return explicitRole;
  }

  if (!token) {
    return "unknown";
  }

  const segments = token.split(".");
  if (segments.length !== 3) {
    return "unknown";
  }

  const payloadSegment = segments[1];
  if (!payloadSegment) {
    return "unknown";
  }

  try {
    if (typeof globalThis.atob !== "function") {
      return "unknown";
    }
    const normalized = payloadSegment.replace(/-/g, "+").replace(/_/g, "/");
    const padded = normalized + "=".repeat((4 - (normalized.length % 4)) % 4);
    const decoded = globalThis.atob(padded);
    const parsed = JSON.parse(decoded) as { role?: string };
    return isKnownRole(parsed.role) ? parsed.role : "unknown";
  } catch {
    return "unknown";
  }
}

function isKnownRole(role: string | undefined): role is AppRole {
  return (
    role === "admin" ||
    role === "analyst" ||
    role === "payer_aggregate_only" ||
    role === "trial_coordinator" ||
    role === "read_only_gov"
  );
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

function normalizePagination(pagination: {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
}): PaginationMeta {
  return {
    page: pagination.page,
    pageSize: pagination.page_size,
    totalItems: pagination.total_items,
    totalPages: pagination.total_pages,
  };
}

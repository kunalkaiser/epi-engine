export type BackendUrlSource =
  | "API_BASE_URL"
  | "BACKEND_URL"
  | "API_URL"
  | "NEXT_PUBLIC_API_BASE_URL"
  | "default";

export type AuthTokenSource = "forwarded_header" | "env_token" | "none";

export type ResolvedBackendConfig = {
  baseUrl: string;
  source: BackendUrlSource;
  configured: boolean;
};

export type ResolvedAuth = {
  authorization: string | null;
  source: AuthTokenSource;
  attached: boolean;
};

export function resolveBackendConfig(): ResolvedBackendConfig {
  const appEnv = (process.env.APP_ENV ?? process.env.NODE_ENV ?? "development").toLowerCase();
  const includePublicFallback = appEnv === "development" || appEnv === "test";
  const candidates: Array<{ key: BackendUrlSource; value: string | undefined }> = [
    { key: "API_BASE_URL", value: process.env.API_BASE_URL },
    { key: "BACKEND_URL", value: process.env.BACKEND_URL },
    { key: "API_URL", value: process.env.API_URL },
    ...(includePublicFallback ? [{ key: "NEXT_PUBLIC_API_BASE_URL" as const, value: process.env.NEXT_PUBLIC_API_BASE_URL }] : []),
  ];

  for (const candidate of candidates) {
    const value = candidate.value?.trim();
    if (value) {
      return {
        baseUrl: value,
        source: candidate.key,
        configured: true,
      };
    }
  }

  return {
    baseUrl: includePublicFallback ? "http://localhost:8000" : "",
    source: "default",
    configured: false,
  };
}

export function resolveAuthorizationHeader(incomingAuthorization: string | null): ResolvedAuth {
  const forwarded = normalizeBearer(incomingAuthorization);
  if (forwarded) {
    return {
      authorization: forwarded,
      source: "forwarded_header",
      attached: true,
    };
  }

  const envAuthorization = normalizeBearer(process.env.API_AUTH_TOKEN ?? null);
  if (envAuthorization) {
    return {
      authorization: envAuthorization,
      source: "env_token",
      attached: true,
    };
  }

  return {
    authorization: null,
    source: "none",
    attached: false,
  };
}

function normalizeBearer(value: string | null): string | null {
  if (!value) {
    return null;
  }

  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }

  const bearerMatch = trimmed.match(/^bearer\s+(.+)$/i);
  if (bearerMatch && bearerMatch[1]) {
    return `Bearer ${bearerMatch[1].trim()}`;
  }

  return `Bearer ${trimmed}`;
}

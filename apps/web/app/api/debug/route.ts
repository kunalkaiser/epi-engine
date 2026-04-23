import { NextRequest, NextResponse } from "next/server";

import { resolveAuthorizationHeader, resolveBackendConfig } from "../../../lib/server-backend";
import type { DebugSnapshot } from "../../../lib/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const KNOWN_ROLES = new Set([
  "admin",
  "analyst",
  "read_only",
  "auditor",
  "operations",
  "payer_aggregate_only",
  "trial_coordinator",
  "read_only_gov",
]);

export async function GET(request: NextRequest) {
  const backend = resolveBackendConfig();
  const auth = resolveAuthorizationHeader(request.headers.get("authorization"));
  const role = decodeRole(auth.authorization);
  const headers = buildUpstreamHeaders(auth.authorization);

  const [backendCheck, catalogCheck, incidenceCheck, indicationCheck] = await Promise.all([
    checkEndpoint(backend.baseUrl, "/health", {}, false, headers),
    checkEndpoint(backend.baseUrl, "/diseases", { page: 1, page_size: 1 }, true, headers),
    checkEndpoint(backend.baseUrl, "/incidence", { page: 1, page_size: 1 }, true, headers),
    checkEndpoint(backend.baseUrl, "/indications/top", { page: 1, page_size: 1, limit: 1 }, true, headers),
  ]);

  const snapshot: DebugSnapshot = {
    frontend: {
      status: "ok",
      detail: "Next.js frontend is serving request-time dashboard data.",
    },
    backend: {
      status: backendCheck.ok ? "ok" : "error",
      detail: backendCheck.detail,
      baseUrl: backend.baseUrl,
      baseUrlSource: backend.source,
      baseUrlConfigured: backend.configured,
    },
    auth: buildAuthStatus(auth, role, [catalogCheck, incidenceCheck, indicationCheck]),
    endpoints: {
      catalog: {
        status: catalogCheck.ok ? "ok" : "error",
        detail: catalogCheck.detail,
      },
      incidence: {
        status: incidenceCheck.ok ? "ok" : "error",
        detail: incidenceCheck.detail,
      },
      indications: {
        status: indicationCheck.ok ? "ok" : "error",
        detail: indicationCheck.detail,
      },
    },
  };

  return NextResponse.json(snapshot, {
    status: 200,
    headers: {
      "cache-control": "no-store",
    },
  });
}

type EndpointResult = {
  ok: boolean;
  detail: string;
};

async function checkEndpoint(
  baseUrl: string,
  path: string,
  query: Record<string, string | number>,
  withAuth: boolean,
  headers: HeadersInit,
): Promise<EndpointResult> {
  let targetUrl: URL;
  try {
    targetUrl = new URL(path, baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`);
    for (const [key, value] of Object.entries(query)) {
      targetUrl.searchParams.set(key, String(value));
    }
  } catch {
    return {
      ok: false,
      detail: `${path} unreachable (backend base URL missing)`,
    };
  }

  let response: Response;
  try {
    response = await fetch(targetUrl.toString(), {
      method: "GET",
      cache: "no-store",
      headers: withAuth ? headers : { Accept: "application/json" },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "unreachable";
    return {
      ok: false,
      detail: `${path} unreachable (${message})`,
    };
  }

  if (response.ok) {
    return {
      ok: true,
      detail: `${path} OK (${response.status})`,
    };
  }

  let detail = `${path} failed (${response.status})`;
  try {
    const body = (await response.json()) as { error?: { message?: string }; detail?: string };
    if (body.error?.message) {
      detail = body.error.message;
    } else if (typeof body.detail === "string") {
      detail = body.detail;
    }
  } catch {
    // Keep default detail.
  }

  return {
    ok: false,
    detail,
  };
}

function buildAuthStatus(
  auth: ReturnType<typeof resolveAuthorizationHeader>,
  role: DebugSnapshot["auth"]["role"],
  checks: EndpointResult[],
): DebugSnapshot["auth"] {
  const missingAuthError = checks.find((check) => check.detail.includes("missing Authorization header"));
  if (!auth.authorization) {
    return {
      status: "error",
      detail: "No Authorization token configured for backend requests.",
      role: "unknown",
      tokenSource: auth.source,
      attached: auth.attached,
    };
  }

  if (missingAuthError) {
    return {
      status: "error",
      detail: missingAuthError.detail,
      role,
      tokenSource: auth.source,
      attached: auth.attached,
    };
  }

  return {
    status: "ok",
    detail: "Authorization header is present for backend requests.",
    role,
    tokenSource: auth.source,
    attached: auth.attached,
  };
}

function buildUpstreamHeaders(authorization: string | null): HeadersInit {
  const headers: Record<string, string> = {
    Accept: "application/json",
  };
  if (authorization) {
    headers.Authorization = authorization;
  }
  return headers;
}

function decodeRole(authorization: string | null): DebugSnapshot["auth"]["role"] {
  if (!authorization) {
    return "unknown";
  }

  const token = authorization.toLowerCase().startsWith("bearer ") ? authorization.slice(7) : authorization;
  const parts = token.split(".");
  if (parts.length !== 3 || !parts[1]) {
    return "unknown";
  }

  try {
    const normalized = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = normalized + "=".repeat((4 - (normalized.length % 4)) % 4);
    const payload = JSON.parse(Buffer.from(padded, "base64").toString("utf-8")) as { role?: string };
    return payload.role && KNOWN_ROLES.has(payload.role) ? (payload.role as DebugSnapshot["auth"]["role"]) : "unknown";
  } catch {
    return "unknown";
  }
}

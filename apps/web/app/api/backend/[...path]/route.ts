import { NextRequest, NextResponse } from "next/server";

import { resolveAuthorizationHeader, resolveBackendConfig } from "../../../../lib/server-backend";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(request: NextRequest, context: { params: Promise<{ path?: string[] }> }) {
  return proxyRequest(request, context);
}

export async function POST(request: NextRequest, context: { params: Promise<{ path?: string[] }> }) {
  return proxyRequest(request, context);
}

async function proxyRequest(request: NextRequest, context: { params: Promise<{ path?: string[] }> }) {
  const params = await context.params;
  const pathSegments = params.path ?? [];
  const upstreamPath = pathSegments.join("/");

  let upstreamResponse: Response;
  try {
    const targetUrl = buildTargetUrl(request, upstreamPath);
    const { authHeader, source } = resolveAuthHeader(request);
    void source;

    const headers = new Headers();
    headers.set("accept", "application/json");
    const requestId = request.headers.get("x-request-id");
    if (requestId) {
      headers.set("x-request-id", requestId);
    }
    if (authHeader) {
      headers.set("authorization", authHeader);
    }

    let body: string | undefined;
    if (request.method !== "GET") {
      body = await request.text();
    }

    upstreamResponse = await fetch(targetUrl, {
      method: request.method,
      cache: "no-store",
      headers,
      body: body && body.length > 0 ? body : undefined,
    });
  } catch (error) {
    const detail = error instanceof Error ? error.message : "unreachable";
    return NextResponse.json(
      {
        error: {
          code: "upstream_unreachable",
          message: `Backend API is unreachable: ${detail}`,
        },
      },
      { status: 502 },
    );
  }

  const body = await upstreamResponse.arrayBuffer();
  const headers = new Headers();
  const contentType = upstreamResponse.headers.get("content-type");
  if (contentType) {
    headers.set("content-type", contentType);
  }

  return new NextResponse(body, {
    status: upstreamResponse.status,
    headers,
  });
}

function buildTargetUrl(request: NextRequest, upstreamPath: string): string {
  const { baseUrl, configured } = resolveBackendConfig();
  if (!configured && !baseUrl) {
    throw new Error("backend base URL is not configured");
  }
  const url = new URL(upstreamPath, baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`);
  request.nextUrl.searchParams.forEach((value, key) => {
    url.searchParams.set(key, value);
  });
  return url.toString();
}

function resolveAuthHeader(request: NextRequest): { authHeader: string | null; source: string } {
  const auth = resolveAuthorizationHeader(request.headers.get("authorization"));
  return {
    authHeader: auth.authorization,
    source: auth.source,
  };
}

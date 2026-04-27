import { createHmac, timingSafeEqual } from "crypto";

export type BackendUrlSource =
  | "API_BASE_URL"
  | "BACKEND_URL"
  | "API_URL"
  | "NEXT_PUBLIC_API_BASE_URL"
  | "default";

export type AuthTokenSource = "forwarded_header" | "env_token" | "generated_token" | "none";

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
  const envToken = extractBearerToken(envAuthorization);
  if (envAuthorization && envToken && isTokenValidForSharedSecret(envToken)) {
    return {
      authorization: envAuthorization,
      source: "env_token",
      attached: true,
    };
  }

  const generatedAuthorization = generateServiceAuthorization();
  if (generatedAuthorization) {
    return {
      authorization: generatedAuthorization,
      source: "generated_token",
      attached: true,
    };
  }

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

function extractBearerToken(value: string | null): string | null {
  if (!value) {
    return null;
  }
  const match = value.match(/^Bearer\s+(.+)$/i);
  if (!match || !match[1]) {
    return null;
  }
  return match[1].trim();
}

function isTokenValidForSharedSecret(token: string): boolean {
  const secret = process.env.AUTH_JWT_SECRET?.trim();
  if (!secret) {
    return true;
  }

  const parts = token.split(".");
  if (parts.length !== 3) {
    return false;
  }
  const [encodedHeader, encodedPayload, encodedSignature] = parts;
  const header = decodeJwtPart(encodedHeader);
  const payload = decodeJwtPart(encodedPayload);
  if (!header || !payload || header.alg !== "HS256" || (header.typ !== undefined && header.typ !== "JWT")) {
    return false;
  }

  const signingInput = `${encodedHeader}.${encodedPayload}`;
  const expectedSignature = createHmac("sha256", secret).update(signingInput).digest();
  const actualSignature = decodeBase64UrlBytes(encodedSignature);
  if (!actualSignature || actualSignature.length !== expectedSignature.length) {
    return false;
  }
  if (!timingSafeEqual(actualSignature, expectedSignature)) {
    return false;
  }

  const issuer = process.env.AUTH_JWT_ISSUER?.trim() || "epi-engine";
  const audience = process.env.AUTH_JWT_AUDIENCE?.trim() || "epi-engine-clients";
  if (payload.iss !== issuer) {
    return false;
  }
  if (Array.isArray(payload.aud)) {
    if (!payload.aud.includes(audience)) {
      return false;
    }
  } else if (payload.aud !== audience) {
    return false;
  }
  if (typeof payload.exp === "number" && payload.exp < Math.floor(Date.now() / 1000)) {
    return false;
  }

  return true;
}

function generateServiceAuthorization(): string | null {
  const secret = process.env.AUTH_JWT_SECRET?.trim();
  if (!secret) {
    return null;
  }

  const issuer = process.env.AUTH_JWT_ISSUER?.trim() || "epi-engine";
  const audience = process.env.AUTH_JWT_AUDIENCE?.trim() || "epi-engine-clients";
  const subject = process.env.API_AUTH_SUB?.trim() || "web-service";
  const role = process.env.API_AUTH_ROLE?.trim() || "analyst";
  const tenantId = process.env.API_AUTH_TENANT_ID?.trim() || "tenant-a";
  const now = Math.floor(Date.now() / 1000);

  const header = { alg: "HS256", typ: "JWT" };
  const payload = {
    sub: subject,
    role,
    iss: issuer,
    aud: audience,
    tenant_id: tenantId,
    exp: now + 3600,
  };

  const encodedHeader = encodeBase64UrlJson(header);
  const encodedPayload = encodeBase64UrlJson(payload);
  const signingInput = `${encodedHeader}.${encodedPayload}`;
  const signature = createHmac("sha256", secret).update(signingInput).digest("base64url");
  return `Bearer ${signingInput}.${signature}`;
}

function encodeBase64UrlJson(value: object): string {
  return Buffer.from(JSON.stringify(value), "utf-8").toString("base64url");
}

function decodeBase64UrlBytes(value: string): Buffer | null {
  try {
    return Buffer.from(value, "base64url");
  } catch {
    return null;
  }
}

function decodeJwtPart(value: string): Record<string, unknown> | null {
  const raw = decodeBase64UrlBytes(value);
  if (!raw) {
    return null;
  }
  try {
    const parsed = JSON.parse(raw.toString("utf-8"));
    if (typeof parsed !== "object" || parsed === null) {
      return null;
    }
    return parsed as Record<string, unknown>;
  } catch {
    return null;
  }
}

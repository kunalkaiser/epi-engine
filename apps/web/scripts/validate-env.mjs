const appEnv = (process.env.APP_ENV || "development").toLowerCase();
const strict = appEnv === "staging" || appEnv === "production";

const errors = [];
const warnings = [];

if (process.env.NEXT_PUBLIC_API_AUTH_TOKEN) {
  errors.push("NEXT_PUBLIC_API_AUTH_TOKEN must never be set (token would leak to browser).");
}

if (strict) {
  if (!process.env.API_BASE_URL) {
    errors.push("API_BASE_URL is required in staging/production web runtime.");
  }
  if (!process.env.API_AUTH_TOKEN) {
    errors.push("API_AUTH_TOKEN is required in staging/production web runtime.");
  }
}

if (!strict && !process.env.API_BASE_URL) {
  warnings.push("API_BASE_URL is not set; dev fallback behavior will be used.");
}

if (errors.length > 0) {
  for (const err of errors) {
    console.error(`[env-check:error] ${err}`);
  }
  process.exit(1);
}

for (const warning of warnings) {
  console.warn(`[env-check:warn] ${warning}`);
}

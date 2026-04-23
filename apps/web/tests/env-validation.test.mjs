import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { test } from "node:test";

test("validate-env blocks NEXT_PUBLIC_API_AUTH_TOKEN", () => {
  const result = spawnSync("node", ["scripts/validate-env.mjs"], {
    cwd: process.cwd(),
    env: {
      ...process.env,
      NEXT_PUBLIC_API_AUTH_TOKEN: "leak",
      APP_ENV: "production",
      API_BASE_URL: "http://api:8000",
      API_AUTH_TOKEN: "token",
    },
    encoding: "utf-8",
  });
  assert.equal(result.status, 1);
  assert.match(result.stderr, /must never be set/);
});

test("validate-env requires server token in production", () => {
  const result = spawnSync("node", ["scripts/validate-env.mjs"], {
    cwd: process.cwd(),
    env: {
      ...process.env,
      APP_ENV: "production",
      API_BASE_URL: "http://api:8000",
      API_AUTH_TOKEN: "",
      NEXT_PUBLIC_API_AUTH_TOKEN: "",
    },
    encoding: "utf-8",
  });
  assert.equal(result.status, 1);
  assert.match(result.stderr, /API_AUTH_TOKEN is required/);
});

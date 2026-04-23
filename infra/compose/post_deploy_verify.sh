#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"
WEB_URL="${WEB_URL:-http://localhost:3000}"

echo "[verify] API health"
curl -fsS "${API_URL}/health" >/tmp/epios-health.json

echo "[verify] API readiness"
curl -fsS "${API_URL}/ready" >/tmp/epios-ready.json

echo "[verify] Web reachability"
curl -fsS -I "${WEB_URL}" >/tmp/epios-web-head.txt

echo "[verify] API metrics (optional)"
if curl -fsS "${API_URL}/metrics" >/tmp/epios-metrics.txt; then
  echo "[verify] metrics endpoint enabled"
else
  echo "[verify] metrics endpoint unavailable (may be disabled by API_METRICS_ENABLED=false)"
fi

echo "[verify] completed"

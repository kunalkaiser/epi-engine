# EPI Engine — Recovery Guide
> Last updated: April 2026  
> If you are reading this, something went wrong. This document tells you exactly how to fix it.

---

## 1. What Was Built

EPI Engine is a pharmaceutical indication prioritisation API backed by ClickHouse Cloud.

| Component | Technology | Live URL |
|-----------|-----------|----------|
| API | FastAPI + Python 3.13 | https://api-production-65d5.up.railway.app |
| Worker | Python background service | Same Railway project, `worker` service |
| Database | ClickHouse Cloud | Set in `CLICKHOUSE_URL` Railway env var |
| Auth | JWT (RS256 / HS256) | Secret in `AUTH_JWT_SECRET` Railway env var |

---

## 2. GitHub Repo

```
github.com/kunalkaiser/epi-engine
```

Deploy:
```bash
cd ~/epi-engine
git push origin main          # triggers Railway auto-deploy (if configured)
# or manually:
railway up --service api --detach
railway up --service worker --detach
```

---

## 3. Railway Services

Project: `epi-engine`  
Dashboard: railway.com → your account → epi-engine project

| Service | Dockerfile | Start command |
|---------|-----------|--------------|
| `api` | `apps/api/Dockerfile` | `uvicorn apps.api.main:app --host 0.0.0.0 --port $PORT` |
| `worker` | `apps/worker/Dockerfile` | `python -m apps.worker.worker` |

Health check path: `/health`  
Metrics path: `/metrics` (enabled by default; disable with `API_METRICS_ENABLED=false`)

---

## 4. Environment Variables — Complete List

Set all of these in Railway → your service → Variables tab.

### API service

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `APP_ENV` | yes | `development` | Set to `production` on Railway |
| `API_LOG_LEVEL` | no | `INFO` | `DEBUG` for troubleshooting |
| `API_HOST` | no | `0.0.0.0` | Leave as-is on Railway |
| `API_PORT` | no | `8000` | Railway sets `$PORT` automatically |
| `API_CORS_ORIGINS` | yes | `http://localhost:3000` | Comma-separated allowed origins |
| `CLICKHOUSE_URL` | yes | — | Full HTTPS URL to ClickHouse Cloud e.g. `https://host.clickhouse.cloud:8443` |
| `CLICKHOUSE_DATABASE` | no | `epi_engine` | |
| `CLICKHOUSE_USER` | yes | `default` | ClickHouse Cloud user |
| `CLICKHOUSE_PASSWORD` | yes | — | ClickHouse Cloud password |
| `CLICKHOUSE_TIMEOUT_SECONDS` | no | `30` | |
| `DB_FALLBACK_ENABLED` | no | `true` | Serve cached data if ClickHouse unreachable |
| `AUTH_JWT_SECRET` | yes | — | HS256 shared secret for JWT signing |
| `AUTH_JWT_ISSUER` | no | `epi-engine` | Must match token `iss` claim |
| `AUTH_JWT_AUDIENCE` | no | `epi-engine-clients` | Must match token `aud` claim |
| `REQUIRE_TENANT_CLAIM_NON_DEV` | no | `true` | Require `tenant_id` in JWT for staging/prod |
| `API_METRICS_ENABLED` | no | `true` | Exposes `/metrics` in Prometheus format |
| `TRACE_HEADER_NAME` | no | `X-Request-ID` | Correlation ID header |
| `PILOT_MODE_ENABLED` | no | `false` | Enables pilot mode label in API responses |
| `PILOT_MODE_LABEL` | no | — | Label text for pilot mode |

### Worker service (add to `worker` service Variables)

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `APP_ENV` | yes | `development` | Set to `production` |
| `CLICKHOUSE_URL` | yes | — | Same as API service |
| `CLICKHOUSE_USER` | yes | — | Same as API service |
| `CLICKHOUSE_PASSWORD` | yes | — | Same as API service |
| `WORKER_LOOP_INTERVAL_SECONDS` | no | `60` | Seconds between job ticks |
| `WORKER_RUN_ONCE` | no | `false` | Set `true` for one-shot runs |
| `WORKER_SIMULATION_BATCH_SIZE` | no | `5` | Simulations processed per tick |
| `WORKER_HEARTBEAT_FILE` | no | `/tmp/epios-worker-heartbeat` | |
| `LIVE_INGESTION_INTERVAL_HOURS` | no | `24` | How often live adapters pull from public APIs |

---

## 5. ClickHouse Cloud — How to Reconnect

If ClickHouse Cloud service ID is lost:

1. Log in at clickhouse.cloud
2. Find the `epi_engine` service
3. Copy the connection string from Settings → Connection Details
4. Format: `https://<host>.clickhouse.cloud:8443`
5. Update `CLICKHOUSE_URL` in both `api` and `worker` Railway services

Schema migrations are in `infra/sql/` — run them in order against ClickHouse Cloud using:
```bash
curl -X POST "https://<host>.clickhouse.cloud:8443/?query=<SQL>" \
  -u "epi_engine_app:<password>"
```

Or use the CLI script:
```bash
CLICKHOUSE_URL=https://... CLICKHOUSE_USER=epi_engine_app CLICKHOUSE_PASSWORD=... \
  python scripts/run_live_ingestion.py --dry-run
```

---

## 5b. New Endpoints — 30-Day Sprint

| Endpoint | Method | Purpose |
|----------|--------|---------|
| /repurposing/opportunities | POST | Cross-indication repurposing candidates with EPI scores |
| /indications/scored | GET | Full scored indication list with confidence intervals |

Worker jobs (both run daily via LIVE_INGESTION_INTERVAL_HOURS=24):
- `live_ingestion`: pulls OpenFDA FAERS, ClinicalTrials.gov, OpenTargets
- `score_recompute`: recalculates EPI scores for all indications in ClickHouse

Seed production data (run once after schema migrations):
```bash
cd ~/epi-engine && python scripts/seed_production_data.py
```

---

## 6. Live Ingestion Sources

The worker pulls from three free public APIs daily:

| Source | Endpoint | Table |
|--------|---------|-------|
| OpenFDA FAERS | `api.fda.gov/drug/event.json` | `epi_engine.live_faers_signals` |
| ClinicalTrials.gov | `clinicaltrials.gov/api/v2/studies` | `epi_engine.live_clinical_trials` |
| OpenTargets | `api.platform.opentargets.org/api/v4/graphql` | `epi_engine.live_open_targets_diseases` |

Run manually:
```bash
cd ~/epi-engine
python scripts/run_live_ingestion.py --dry-run   # check without writing
python scripts/run_live_ingestion.py             # live write to ClickHouse
```

---

## 7. Rate Limiting

The API uses slowapi (200 req/min per IP globally).  
Indication endpoints (`/indications/ranked`, `/indications/top`) are limited to 60 req/min.  
429 Too Many Requests is returned when exceeded — clients should back off and retry after 60 seconds.

---

## 8. Metrics Endpoint

`GET /metrics` returns Prometheus-format text:
```
epios_api_up 1
epios_api_ready 1
```

Used by Railway health monitoring. Disable with `API_METRICS_ENABLED=false`.

---

## 9. If Services Go Down

| Scenario | Impact | Fix |
|----------|--------|-----|
| Railway API down | Indication panel in Evidara shows "unavailable" — graceful | `railway up --service api --detach` |
| Railway Worker down | Live ingestion pauses; existing data served | `railway up --service worker --detach` |
| ClickHouse Cloud down | API falls back to empty/cached responses if `DB_FALLBACK_ENABLED=true` | Wait for ClickHouse recovery |
| Rate limit triggered | 429 from legitimate burst | Increase limit or add IP allowlist |
| JWT secret rotated | All existing tokens invalid — users get 401 | Update `AUTH_JWT_SECRET` then re-issue tokens |

---

## 10. Local Development

```bash
cd ~/epi-engine

# Start ClickHouse locally via Docker
docker compose up clickhouse -d

# Run API
APP_ENV=development uvicorn apps.api.main:app --reload --port 8000

# Run worker once
WORKER_RUN_ONCE=true python -m apps.worker.worker
```

---

## 11. Architecture Laws

1. Association is NEVER upgraded to causation in any API response
2. EPI scores are associative ranking heuristics — labeled as such in every response
3. ClickHouse schema migrations are in `infra/sql/` — run in numeric order
4. Worker heartbeat file written every tick — if stale > 10 min, worker is dead
5. JWT is required for all non-health endpoints in staging/production

---

*Rotate `AUTH_JWT_SECRET` and `CLICKHOUSE_PASSWORD` every 90 days.*  
*Kunal Chaudhary, PhD, MHA · Evidara · hello@evidara.ai*

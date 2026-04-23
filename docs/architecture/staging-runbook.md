# Staging Operator Runbook

This runbook documents staging operations. Automated deploy via GitHub Actions is the default path; manual deploy is fallback.

## Current staging architecture

- Runtime target: single-host Docker Compose.
- Services:
  - `api` (FastAPI)
  - `web` (Next.js)
  - `worker` (Python worker scheduler loop)
  - `clickhouse` (analytics database)
- Access path: Cloudflare Tunnel + Cloudflare Access for private staging preview.

## Prerequisites

1. Staging host has Docker/Compose installed.
2. Repo is cloned on staging host (example path: `/opt/epi-engine`).
3. `.env.staging` exists with non-dev values.
4. Cloudflare tunnel credential JSON exists on host and is readable by `cloudflared`.
5. Cloudflare DNS and Access apps/policies are already configured.
6. Deploy SSH account is least-privilege and restricted to deployment operations.

## Automated deploy flow (default)

1. Push to `main` (or manual workflow dispatch).
2. GitHub Actions runs build, test, package.
3. Deploy job waits on protected `staging` environment approval rules (required reviewers, prevent self-review).
4. Workflow deploys to staging host over SSH and runs verify checks.
5. Manual deploy path is used only as fallback when automation transport is unavailable.
6. Cloudflare edge access is provided by the optional `cloudflared` compose profile mapped to `staging.epi-engine.example`.

## Manual deploy flow (fallback)

### 1) Pull latest baseline from GitHub

```bash
cd /opt/epi-engine
git fetch origin
git checkout main
git pull --ff-only origin main
```

### 2) Preflight config and environment

```bash
docker compose --env-file .env.staging \
  -f docker-compose.yml \
  -f docker-compose.staging.yml \
  config
```

Checks:

1. `DB_FALLBACK_ENABLED=false` in resolved API env.
2. `AUTH_JWT_SECRET`, `CLICKHOUSE_PASSWORD`, and `API_AUTH_TOKEN` are not dev defaults.
3. Staging hostnames and Cloudflare routing values match operator configuration.
4. `API_METRICS_ENABLED`, `TRACE_HEADER_NAME`, and `WORKER_HEARTBEAT_FILE` are set.

### 3) Build and deploy

```bash
docker compose --env-file .env.staging \
  -f docker-compose.yml \
  -f docker-compose.staging.yml \
  up -d --build
```

### 4) Apply ClickHouse schema in order (only when schema changes)

```bash
docker exec -i $(docker ps -qf name=clickhouse) clickhouse-client < infra/sql/001_init_schema.sql
docker exec -i $(docker ps -qf name=clickhouse) clickhouse-client < infra/sql/002_staging_tables.sql
docker exec -i $(docker ps -qf name=clickhouse) clickhouse-client < infra/sql/004_enterprise_aggregate_extensions.sql
docker exec -i $(docker ps -qf name=clickhouse) clickhouse-client < infra/sql/005_phase2_persistence_and_tenant.sql
docker exec -i $(docker ps -qf name=clickhouse) clickhouse-client < infra/sql/006_phase3_intelligence_async_simulation.sql
```

Do not apply `infra/sql/003_dev_seed_indication_profile_facts.sql` in staging.

### 5) Verify application and access

1. Service health:
   - `curl http://localhost:8000/health`
   - `curl http://localhost:8000/ready`
   - `curl -I http://localhost:3000`
   - `bash infra/compose/post_deploy_verify.sh`
2. Cloudflare Access behavior:
   - Unauthenticated requests receive Access challenge.
   - Authenticated SSO users can load web and API.
3. API runtime:
   - Aggregate-only behavior preserved.
   - No synthetic fallback usage in staging logs.
4. Worker health:
   - `docker inspect --format '{{json .State.Health}}' $(docker ps -qf name=worker)`
   - heartbeat timestamp updates under `${WORKER_HEARTBEAT_FILE}`.

## Secrets and access ownership

- Deployment secrets and auth values are operator-managed:
  - API/JWT secrets
  - DB credentials
  - web auth token
  - Cloudflare tunnel credentials
- Cloudflare Access controls are operator/security-team managed:
  - IdP groups
  - session settings
  - device posture checks
  - service token scopes

These values are org-specific and are not hardcoded in this repository.

## Manual vs automated (current state)

- Automated by default:
  - GitHub Actions workflow `.github/workflows/staging.yml`
  - build, test, package, deploy, and verify stages on pushes to `main` and manual dispatch
  - deployment gated by protected `staging` environment
- Still manual/operator-owned:
  - Cloudflare Access policy changes
  - secret rotation and distribution
  - emergency fallback deploy from staging host shell

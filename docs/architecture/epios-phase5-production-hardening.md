# EpiOS Phase 5: Production Hardening

Phase 5 focuses on deployment safety, configuration rigor, observability, security posture, and operational runbooks.

## 1. Environment and Secret Hardening

Implemented:

- API startup validation in `apps/api/settings.py`:
  - `APP_ENV` must be one of `development|test|staging|production`
  - non-dev rejects:
    - `DB_FALLBACK_ENABLED=true`
    - weak/missing `AUTH_JWT_SECRET`
    - localhost ClickHouse URL
    - default/empty ClickHouse credentials
    - localhost CORS origins
- Web runtime env guard: `apps/web/scripts/validate-env.mjs`
  - forbids `NEXT_PUBLIC_API_AUTH_TOKEN`
  - requires `API_BASE_URL` and `API_AUTH_TOKEN` in staging/production
- Worker startup validation in `apps/worker/worker.py`
  - non-dev rejects localhost ClickHouse URL
  - rejects excessive worker loop interval
- New env examples:
  - `.env.staging.example` (expanded)
  - `.env.production.example` (added)

## 2. Deployment Readiness Hardening

Implemented:

- Compose healthchecks for `api`, `web`, `clickhouse`, `worker` in `docker-compose.yml`
- Dependency sequencing via `condition: service_healthy`
- Worker heartbeat file support:
  - `WORKER_HEARTBEAT_FILE` env
  - written each worker tick
- Post-deploy verification script:
  - `infra/compose/post_deploy_verify.sh`
  - validates API health/ready + web reachability + metrics availability

## 3. Observability and Diagnostics

Implemented:

- Secret redaction in structured logging:
  - `apps/api/logging_utils.py`
  - redacts fields containing password/secret/token/authorization/api_key/credential
- Trace header configurability:
  - `TRACE_HEADER_NAME` setting (default `X-Request-ID`)
  - middleware reads and returns configured correlation header
- Frontend request ID propagation:
  - `apps/web/lib/api.ts` sends `X-Request-ID`
  - backend proxy forwards `x-request-id`
- Runtime diagnostics enriched:
  - `metrics_enabled`
  - `trace_header_name`
  - `queued_simulation_runs` backlog signal

## 4. Security Operations Hardening

Implemented:

- CI and staging gates block accidental `NEXT_PUBLIC_API_AUTH_TOKEN` usage
- Non-dev configuration validation fails fast before serving traffic
- Secret-bearing values are redacted in logs by default utility
- Aggregate-only behavior remains unchanged; no patient-level endpoint added

## 5. CI/CD and Release Safety

Implemented:

- New CI workflow: `.github/workflows/ci.yml`
  - security gate (public token env check)
  - Python tests
  - web env validation + build
- Staging workflow strengthened (`.github/workflows/staging.yml`)
  - security gate for forbidden public token usage
  - explicit web env values for validation/build

## 6. Testing Additions

Added/updated tests:

- `tests/test_logging_redaction.py`
- `tests/test_settings.py` non-dev fail-fast coverage
- `tests/test_worker_runtime.py` heartbeat + non-dev validation
- `tests/test_runtime_assumptions.py`
  - compose healthcheck assumptions
  - env example expectations
  - web env validator expectations
- frontend node test harness:
  - `apps/web/tests/env-validation.test.mjs`
  - `npm run test:node`

## 7. Failure Modes and Operational Expectations

### API startup failure
- Cause: invalid non-dev env config.
- Behavior: process exits fast via `ValueError` from settings validation.
- Operator action: correct env file/secret values and restart.

### Worker degraded or stalled
- Signal: worker healthcheck fails due stale heartbeat.
- Action:
  1. inspect worker logs
  2. verify ClickHouse connectivity
  3. restart worker service

### Simulation queue growth
- Signal: `/debug/runtime` shows `queued_simulation_runs`.
- Action:
  1. increase worker throughput (`WORKER_SIMULATION_BATCH_SIZE`)
  2. reduce loop interval
  3. inspect failed/retried runs for poison payloads

### Metrics endpoint disabled
- Signal: `/metrics` returns 404.
- Cause: `API_METRICS_ENABLED=false`.
- Action: enable only when scrape path is expected in environment.

## 8. Backup/Recovery Baseline

Operator-owned prerequisites (external to repo):

- ClickHouse persistent volume snapshots
- backup retention policy
- restore drills per environment
- secret manager backups for auth/deploy credentials

Minimum restore validation:

1. Restore ClickHouse volume or tables.
2. Re-apply migration SQL in order.
3. Run `infra/compose/post_deploy_verify.sh`.
4. Validate simulation run reads and data-quality views.

## 9. What Remains External

Still operator/cloud managed (not repo-enforced):

- secret manager lifecycle and rotation
- alert routing (PagerDuty/Opsgenie/etc.)
- central log/metrics backend
- Cloudflare Access/IdP policy objects
- GitHub environment protection reviewer policy

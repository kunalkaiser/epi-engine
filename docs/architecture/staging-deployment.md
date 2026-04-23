# Staging Deployment Checklist

This repository currently targets a single-host Docker Compose staging deployment.

## Folder-to-deployment map

- `apps/api`: FastAPI service container (`apps/api/Dockerfile`).
- `apps/web`: Next.js service container (`apps/web/Dockerfile`).
- `apps/worker`: background worker container (`apps/worker/Dockerfile`).
- `infra/sql`: ClickHouse schema and staging tables (`001_init_schema.sql`, `002_staging_tables.sql`, `004_enterprise_aggregate_extensions.sql`, `005_phase2_persistence_and_tenant.sql`, `006_phase3_intelligence_async_simulation.sql`).
- `docker-compose.yml`: local/dev baseline wiring.
- `docker-compose.staging.yml`: staging override (strict env, persistent ClickHouse volume, fallback disabled).

## Pre-deploy checks

1. Copy `.env.staging.example` to `.env.staging` and set real values.
2. Confirm secrets are not dev defaults:
   - `AUTH_JWT_SECRET`
   - `CLICKHOUSE_PASSWORD`
   - `API_AUTH_TOKEN`
3. Confirm API fallback is disabled in staging (`DB_FALLBACK_ENABLED=false` in staging compose override).
4. Confirm the app uses aggregate-only data paths and does not include patient-level exports.

## Boot staging stack

Preflight the resolved compose config first (fails fast on missing required env vars):

```bash
docker compose --env-file .env.staging \
  -f docker-compose.yml \
  -f docker-compose.staging.yml \
  config
```

Then start the stack:

```bash
docker compose --env-file .env.staging \
  -f docker-compose.yml \
  -f docker-compose.staging.yml \
  up -d --build
```

## Runtime startup commands (from container images/compose)

- API: `uvicorn apps.api.main:app --host 0.0.0.0 --port 8000`
- Web: `npm run start -- --hostname 0.0.0.0 --port 3000`
- Worker: `python -m apps.worker.worker`

## Frontend route and HTML artifact

- Public-facing frontend route: `/` on the `web` service.
- Front page source: `apps/web/app/page.tsx` (Next.js App Router).
- HTML is served by `next start` from the production `.next` build artifact generated during image build (`RUN npm run build` in `apps/web/Dockerfile`).

## Apply ClickHouse schema

Apply in this exact order:

```bash
docker exec -i $(docker ps -qf name=clickhouse) clickhouse-client < infra/sql/001_init_schema.sql
docker exec -i $(docker ps -qf name=clickhouse) clickhouse-client < infra/sql/002_staging_tables.sql
docker exec -i $(docker ps -qf name=clickhouse) clickhouse-client < infra/sql/004_enterprise_aggregate_extensions.sql
docker exec -i $(docker ps -qf name=clickhouse) clickhouse-client < infra/sql/005_phase2_persistence_and_tenant.sql
docker exec -i $(docker ps -qf name=clickhouse) clickhouse-client < infra/sql/006_phase3_intelligence_async_simulation.sql
```

Do not apply `infra/sql/003_dev_seed_indication_profile_facts.sql` in staging.

## Smoke checks

1. API health: `curl http://localhost:8000/health`
2. Web health: `curl -I http://localhost:3000`
3. API authenticated endpoint with staging token: `/diseases` or `/indications/top`
4. Verify API logs do not show synthetic fallback usage in staging.

## First post-push staging/access pass

Use this after a new commit is pushed to GitHub `main`.

### 1) Pull latest code on the staging host

```bash
cd /opt/epi-engine
git fetch origin
git checkout main
git pull --ff-only origin main
```

### 2) Reconcile staging environment

1. Verify `.env.staging` still has non-dev secrets and correct staging hostnames.
2. Verify Cloudflare tunnel credentials file exists on host and is readable by `cloudflared`.
3. Re-run compose preflight:

```bash
docker compose --env-file .env.staging \
  -f docker-compose.yml \
  -f docker-compose.staging.yml \
  config
```

### 3) Deploy and apply schema (if changed)

```bash
docker compose --env-file .env.staging \
  -f docker-compose.yml \
  -f docker-compose.staging.yml \
  up -d --build
```

Apply ClickHouse SQL in order when schema changes are present:

1. `infra/sql/001_init_schema.sql`
2. `infra/sql/002_staging_tables.sql`
3. `infra/sql/004_enterprise_aggregate_extensions.sql`
4. `infra/sql/005_phase2_persistence_and_tenant.sql`
5. `infra/sql/006_phase3_intelligence_async_simulation.sql`

### 4) Validate Cloudflare access path

1. Confirm DNS CNAMEs still target `<tunnel-id>.cfargotunnel.com` in proxied mode.
2. Confirm unauthenticated request to `https://staging.epi-engine.example` gets Access challenge.
3. Confirm authenticated SSO user can open web and call API through:
   - `https://staging.epi-engine.example`
   - `https://staging-api.epi-engine.example/health`

### 5) Validate Access policy posture

1. Confirm only approved IdP groups are allowed.
2. Confirm MFA requirement remains enabled.
3. Confirm deny-by-default remains enabled.

Policy values (IdP groups, session durations, device checks, service token scopes) are org-specific and operator-managed.

## Cloudflare staging access (private preview)

Use Cloudflare Tunnel + Cloudflare Access so staging stays private and does not require opening inbound firewall ports.

### Target access model

- Public entrypoints:
  - `staging.epi-engine.example` -> web (`http://web:3000`)
  - `staging-api.epi-engine.example` -> api (`http://api:8000`)
- Internal services (`clickhouse`, `worker`) stay private on Docker network.
- Cloudflare Access enforces SSO before a request reaches staging services.

### Prerequisites

1. Cloudflare-managed DNS zone for your staging domain.
2. Cloudflare Zero Trust account enabled.
3. SSO IdP configured in Access (Okta, Entra ID, Google Workspace, etc.).
4. A service account/token permitted to create tunnels and DNS records.
5. Operator-owned secure storage for tunnel credential JSON and Access policy values.

### Tunnel setup steps

1. Create a tunnel in Cloudflare Zero Trust and store the generated tunnel credentials JSON securely.
2. Add public hostnames in tunnel ingress:
   - `staging.epi-engine.example` -> `http://web:3000`
   - `staging-api.epi-engine.example` -> `http://api:8000`
3. Add DNS CNAME records from both hostnames to the tunnel endpoint (`<tunnel-id>.cfargotunnel.com`) using proxied mode.
4. Run `cloudflared` alongside the compose stack using the optional compose profile and the config at `infra/docker/cloudflared/config.staging.example.yml`.
   - `CLOUDFLARE_TUNNEL_CREDENTIALS_FILE` in `.env.staging` must point to the host path of the tunnel credentials JSON mounted into the `cloudflared` container.

Example (staging host):

```bash
docker compose --env-file .env.staging \
  -f docker-compose.yml \
  -f docker-compose.staging.yml \
  --profile cloudflare \
  up -d --build
```

This keeps the existing `api/web/worker/clickhouse` topology intact and adds `cloudflared` only as an edge sidecar.

### Host-side tunnel wiring (explicit)

Use these exact host-side paths/values unless your ops standard requires different locations:

1. Tunnel credentials JSON on host:
   - Recommended path: `/opt/epi-engine/secrets/cloudflared/tunnel-credentials.json`
   - `.env.staging` value:
     - `CLOUDFLARE_TUNNEL_CREDENTIALS_FILE=/opt/epi-engine/secrets/cloudflared/tunnel-credentials.json`
   - Expected permissions:
     - directory `0700` (owner-only)
     - file `0600` (owner-only read/write)
2. `cloudflared` config file in repo:
   - Host path: `infra/docker/cloudflared/config.staging.example.yml`
   - Container mount path: `/etc/cloudflared/config.yml`
   - Ingress rules location: `infra/docker/cloudflared/config.staging.example.yml` under `ingress:`
3. Tunnel start command (compose-managed `cloudflared` service):
   - Container command:
     - `cloudflared tunnel --no-autoupdate --config /etc/cloudflared/config.yml run`
   - Host invocation:
```bash
docker compose --env-file .env.staging \
  -f docker-compose.yml \
  -f docker-compose.staging.yml \
  --profile cloudflare \
  up -d --build
```

### Live frontend hostname and access model

- Frontend live URL: `https://staging.epi-engine.example`
- Deployment target: self-hosted `web` service (`http://web:3000`) behind Cloudflare Tunnel.
- Access model: **Access-protected** by default (recommended for staging).
- If operators choose a public page instead, they must change Cloudflare Access policies outside this repository.

### Cloudflare operator checklist (required)

1. Create or select a Cloudflare Tunnel and keep its credentials JSON on the staging host.
2. Set `CLOUDFLARE_TUNNEL_CREDENTIALS_FILE` in `.env.staging` to that host path.
3. Configure tunnel ingress hostnames:
   - `staging.epi-engine.example` -> `http://web:3000`
   - `staging-api.epi-engine.example` -> `http://api:8000`
4. Configure DNS CNAME records (proxied) for both hostnames to `<tunnel-id>.cfargotunnel.com`.
5. Configure Cloudflare Access apps/policies for staging hostnames.
6. Start compose with `--profile cloudflare` and verify the front page at `https://staging.epi-engine.example`.
7. Verify host-side credential wiring:
   - `test -f "$CLOUDFLARE_TUNNEL_CREDENTIALS_FILE"`
   - `ls -l "$CLOUDFLARE_TUNNEL_CREDENTIALS_FILE"` confirms owner-only file access
   - `docker compose --env-file .env.staging -f docker-compose.yml -f docker-compose.staging.yml --profile cloudflare config` resolves without missing-variable errors

Important:

- Tunnel, DNS, and Access objects are operator-managed in Cloudflare and are not provisioned by repo code.
- Access policy values (IdP groups, session settings, posture checks, token scopes) remain operator/security-managed.

### Access policy baseline (staging)

Create Access applications for both staging hostnames:

1. `staging-web` app for `staging.epi-engine.example`
2. `staging-api` app for `staging-api.epi-engine.example`

Recommended minimum policy:

1. Allow only corporate IdP users in approved groups (for example `epi-engine-staging-users`).
2. Require MFA.
3. Deny by default for everyone else.
4. Keep API and web policies separate so API access can be narrower.

### SSO and identity notes

- Prefer group-based policy rules over individual emails.
- If service-to-service API calls are needed later, use Cloudflare Access service tokens with least privilege.
- Keep Cloudflare identity policy aligned with internal RBAC roles, but do not rely on Access alone for app authorization.
- Group names, SSO claims, and session controls are org-specific and must be maintained by operators/security admins.

### Operator checklist for Cloudflare cutover

1. Confirm `.env.staging` domain values match Cloudflare hostnames.
2. Validate tunnel routes with `cloudflared tunnel route dns`.
3. Verify unauthenticated access gets Access login challenge.
4. Verify authenticated access reaches `/health` and web home page.
5. Confirm staging logs do not include PHI and still enforce aggregate-only behavior.

## Minimum CI/CD plan for staging

Current state: staging deployment is automated through GitHub Actions with environment protection on `staging`. Manual deployment remains the fallback path.

### Stage 1: Build

1. Build API, web, and worker container images from existing Dockerfiles.
2. Fail on Docker build errors.

### Stage 2: Test

1. Run unit/integration tests (`python3 -m pytest tests`).
2. Optionally run frontend type/build checks as part of image build already.

### Stage 3: Package

1. Tag images using commit SHA and optionally a `staging` tag.
2. Publish images to an org-approved container registry.

### Stage 4: Deploy (staging)

1. Trigger on push to `main` or manual dispatch.
2. Deploy job runs only in protected GitHub environment `staging`.
3. On staging host over SSH:
   - pull latest `main`
   - run `docker compose ... config` preflight
   - run `docker compose ... up -d --build`
   - apply `001_init_schema.sql`, `002_staging_tables.sql`, `004_enterprise_aggregate_extensions.sql`, `005_phase2_persistence_and_tenant.sql`, and `006_phase3_intelligence_async_simulation.sql` (configurable on manual dispatch).

### Stage 5: Verify

1. API `/health` and web status check.
2. Authenticated API smoke request.
3. Cloudflare Access challenge + authenticated access validation.
4. Confirm no synthetic fallback usage in staging logs.

### Secrets and access configuration in CI/CD context

- Secrets/tokens should be stored in the CI platform secret manager and/or an org secret vault, not in repo files.
- Cloudflare tunnel credentials should be managed as operator secrets on staging host or secure secret backend.
- Cloudflare policy values remain operator-owned and org-specific:
  - IdP groups
  - session settings
  - posture checks
  - token scopes

## GitHub Actions staging deploy workflow

The repository includes a staging deploy workflow:

- `.github/workflows/staging.yml`
- Triggers:
  - push to `main`
  - manual `workflow_dispatch`

The workflow contains explicit stages:

1. Build: build `api`, `web`, `worker` images from existing Dockerfiles.
2. Test: run Python tests and web build check.
3. Package: upload a small staging bundle artifact (compose files, SQL, runbook/docs, metadata).
4. Deploy: remote SSH deploy on protected `staging` environment.
5. Verify: remote compose assertions and health checks.

Important guardrails:

- Runtime topology is unchanged (`api/web/worker/clickhouse` via compose).
- No secrets are stored in repo.
- Deploy is gated by GitHub environment protection/approval on `staging`.
- Required deploy transport secrets are operator-managed in GitHub environment/repo secrets.
- Manual deploy path is retained as fallback if CI/CD transport is unavailable.

## Staging go-live checklist (operator)

Use this checklist before enabling automated staging deploys for go-live.

1. Confirm workflow wiring:
   - `.github/workflows/staging.yml` exists on `main`.
   - Deploy job uses `environment: staging`.
2. Confirm protected environment settings in GitHub:
   - Required reviewers enabled for `staging`.
   - Prevent self-review enabled.
   - Deployment branch rule restricted to `main` (recommended).
3. Configure required secrets (in GitHub environment/repo settings, never in git):
   - `STAGING_DEPLOY_HOST`
   - `STAGING_DEPLOY_USER`
   - `STAGING_DEPLOY_SSH_KEY`
   - `STAGING_DEPLOY_KNOWN_HOSTS`
   - `STAGING_DEPLOY_PATH` (optional, defaults to `/opt/epi-engine`)
4. Confirm SSH hardening and host prerequisites:
   - `STAGING_DEPLOY_USER` is a least-privilege deploy account, not a personal admin user.
   - Deploy account has only the permissions needed to run git pull + docker compose in deploy path.
   - `known_hosts` pinning is provided and validated (no host-key prompts).
   - Staging host has Docker/Compose and `.env.staging` pre-provisioned.
5. Confirm runtime topology remains unchanged:
   - `api`, `web`, `worker`, `clickhouse` via compose.
6. Confirm policy ownership boundaries:
   - Cloudflare Access policy values remain outside code and operator/security-managed.
   - IdP groups, session settings, posture checks, and token scopes are org-specific.
7. Run first controlled deploy:
   - Trigger workflow from `main` (or `workflow_dispatch`).
   - Approve `staging` environment deployment through required reviewer flow.
   - Verify API/web health and compose assertions pass.

## Enforcement boundary (what is enforced where)

- Enforced in repo/workflow code:
  - build/test/package/deploy/verify stage order
  - deploy job bound to `staging` environment
  - required secret presence checks in deploy job
  - SSH strict host key checking and known_hosts use
  - compose assertions for staging (`DB_FALLBACK_ENABLED=false`, `CLICKHOUSE_DB`)
- Enforced in GitHub settings (outside repo code):
  - required reviewers
  - prevent self-review
  - deployment branch restrictions
  - actual secret values and rotation lifecycle
- Operator/security-owned (outside repo code):
  - Cloudflare Access policy configuration and governance
  - IdP groups, session settings, posture checks, token scopes
  - staging host hardening and least-privilege user controls

### Go-live configuration matrix

| Control | Enforced by | Exact required setting/value |
|---|---|---|
| Deploy approval gate | GitHub UI (`staging` environment) | Enable required reviewers |
| No self-approval | GitHub UI (`staging` environment) | Enable `Prevent self-review` |
| Allowed deploy branch | GitHub UI (`staging` environment) | Restrict deployment branches to `main` |
| Deploy workflow wiring | Repo (`.github/workflows/staging.yml`) | `deploy` job includes `environment: staging` |
| Required deploy secrets presence | Repo workflow runtime | Fails deploy job if required secrets are missing |
| Required secrets | GitHub Secrets (env/repo) | `STAGING_DEPLOY_HOST`, `STAGING_DEPLOY_USER`, `STAGING_DEPLOY_SSH_KEY`, `STAGING_DEPLOY_KNOWN_HOSTS`, optional `STAGING_DEPLOY_PATH` |
| SSH host verification | Repo workflow + operator secret value | `StrictHostKeyChecking=yes` with pinned `known_hosts` secret |
| Compose topology | Repo compose files | `api`, `web`, `worker`, `clickhouse` only |
| Cloudflare Access policy governance | Operator/security | IdP groups, session settings, posture checks, token scopes (outside repo code) |

Validation note:

- Repo checks can validate workflow wiring and required secret names, but cannot validate GitHub UI protection settings until those are configured in repository settings.

### Required GitHub environment and secrets

Configure GitHub environment `staging` with required protection rules (for example required reviewers) and these secrets:

1. `STAGING_DEPLOY_HOST`
2. `STAGING_DEPLOY_USER`
3. `STAGING_DEPLOY_SSH_KEY`
4. `STAGING_DEPLOY_KNOWN_HOSTS`
5. `STAGING_DEPLOY_PATH` (optional; defaults to `/opt/epi-engine`)

Required GitHub environment protection settings:

1. `Settings -> Environments -> staging -> Required reviewers`: enabled with at least one staging approver group/user.
2. `Prevent self-review`: enabled so the triggering actor cannot self-approve deployment.
3. `Deployment branches`: restrict to `main` (recommended for this workflow).

Notes:

- Secrets remain outside the repo.
- Cloudflare Access policy values remain operator/security-managed and org-specific:
  - IdP groups
  - session settings
  - posture checks
  - token scopes

## Phase 5 hardening additions

Runtime validation and health hardening now included:

1. API and worker fail fast on unsafe staging/production config.
2. Compose healthchecks are defined for `api`, `web`, `clickhouse`, and `worker`.
3. Web startup/build validates runtime env (`apps/web/scripts/validate-env.mjs`) and blocks `NEXT_PUBLIC_API_AUTH_TOKEN`.
4. Worker heartbeat file is used for health signaling:
   - `WORKER_HEARTBEAT_FILE=/tmp/epios-worker-heartbeat`
5. New env knobs:
   - `API_METRICS_ENABLED`
   - `TRACE_HEADER_NAME`

Post-deploy verification helper:

```bash
API_URL=http://localhost:8000 WEB_URL=http://localhost:3000 \
  bash infra/compose/post_deploy_verify.sh
```

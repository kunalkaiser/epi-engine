# Staging Deployment Checklist

This repository currently targets a single-host Docker Compose staging deployment.

## Folder-to-deployment map

- `apps/api`: FastAPI service container (`apps/api/Dockerfile`).
- `apps/web`: Next.js service container (`apps/web/Dockerfile`).
- `apps/worker`: background worker container (`apps/worker/Dockerfile`).
- `infra/sql`: ClickHouse schema and staging tables (`001_init_schema.sql`, `002_staging_tables.sql`).
- `docker-compose.yml`: local/dev baseline wiring.
- `docker-compose.staging.yml`: staging override (strict env, persistent ClickHouse volume, fallback disabled).

## Pre-deploy checks

1. Copy `.env.staging.example` to `.env.staging` and set real values.
2. Confirm secrets are not dev defaults:
   - `AUTH_JWT_SECRET`
   - `CLICKHOUSE_PASSWORD`
   - `NEXT_PUBLIC_API_AUTH_TOKEN`
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
- Worker (current staging scaffold): `python -c "import time; print('worker ready (staging)'); time.sleep(10**9)"`

The worker command above is a staging boot placeholder, not a production job scheduler.

## Apply ClickHouse schema

Apply in this exact order:

```bash
docker exec -i $(docker ps -qf name=clickhouse) clickhouse-client < infra/sql/001_init_schema.sql
docker exec -i $(docker ps -qf name=clickhouse) clickhouse-client < infra/sql/002_staging_tables.sql
```

Do not apply `infra/sql/003_dev_seed_indication_profile_facts.sql` in staging.

## Smoke checks

1. API health: `curl http://localhost:8000/health`
2. Web health: `curl -I http://localhost:3000`
3. API authenticated endpoint with staging token: `/diseases` or `/indications/top`
4. Verify API logs do not show synthetic fallback usage in staging.

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

### Tunnel setup steps

1. Create a tunnel in Cloudflare Zero Trust and store the generated tunnel credentials JSON securely.
2. Add public hostnames in tunnel ingress:
   - `staging.epi-engine.example` -> `http://web:3000`
   - `staging-api.epi-engine.example` -> `http://api:8000`
3. Add DNS CNAME records from both hostnames to the tunnel endpoint (`<tunnel-id>.cfargotunnel.com`) using proxied mode.
4. Run `cloudflared` alongside the compose stack using a config based on `infra/docker/cloudflared/config.staging.example.yml`.

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

### Operator checklist for Cloudflare cutover

1. Confirm `.env.staging` domain values match Cloudflare hostnames.
2. Validate tunnel routes with `cloudflared tunnel route dns`.
3. Verify unauthenticated access gets Access login challenge.
4. Verify authenticated access reaches `/health` and web home page.
5. Confirm staging logs do not include PHI and still enforce aggregate-only behavior.

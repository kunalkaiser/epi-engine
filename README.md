# EPI Engine

Minimal scaffold for the EPI Engine healthcare epidemiology decision-support platform.

## Main Dev Flows

### 1. Run the API

From the repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r apps/api/requirements.txt
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.

### 2. Run the Web App

In a separate shell:

```bash
cd apps/web
npm ci
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 \
NEXT_PUBLIC_API_AUTH_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkZXYtYW5hbHlzdCIsInJvbGUiOiJhbmFseXN0IiwiaXNzIjoiZXBpLWVuZ2luZSIsImF1ZCI6ImVwaS1lbmdpbmUtY2xpZW50cyJ9.fgEAYuZ1C514IX5-wlL5gpG1KUrp3kQepCxz52jLJMY \
npm run dev
```

The web app will be available at `http://localhost:3000`.

Notes:
- `NEXT_PUBLIC_API_AUTH_TOKEN` must be a bearer token signed with the API JWT settings.
- `docker compose up --build` provides a default dev analyst token so the browser flows work from a clean checkout.
- The token above is a local development token only and matches the compose defaults.

### 3. Run Tests

From the repo root:

```bash
python3 -m pytest tests
```

## Docker Compose

The compose file wires the API, web app, and ClickHouse together and includes a default dev analyst token for local use only.

```bash
docker compose up --build
```

Services:
- API: `http://localhost:8000`
- Web: `http://localhost:3000`
- ClickHouse: `http://localhost:8123`
- Worker: background worker container (development stub process for compose boot verification)

## Staging Deployment Path

Use compose base + staging override with explicit env values:

```bash
cp .env.staging.example .env.staging
docker compose --env-file .env.staging \
  -f docker-compose.yml \
  -f docker-compose.staging.yml \
  config
docker compose --env-file .env.staging \
  -f docker-compose.yml \
  -f docker-compose.staging.yml \
  up -d --build
```

Then apply ClickHouse schema files:

```bash
docker exec -i $(docker ps -qf name=clickhouse) clickhouse-client < infra/sql/001_init_schema.sql
docker exec -i $(docker ps -qf name=clickhouse) clickhouse-client < infra/sql/002_staging_tables.sql
```

Full checklist: `docs/architecture/staging-deployment.md`.

Cloudflare private staging access guidance (Tunnel + Access policies): `docs/architecture/staging-deployment.md`.

Staging-only behavior:
- `DB_FALLBACK_ENABLED=false` is enforced in `docker-compose.staging.yml` so synthetic API fallback is disabled.
- `infra/sql/003_dev_seed_indication_profile_facts.sql` is development-only and should not be applied in staging.

## GitHub First Push

Recommended first commit message:

```text
chore: baseline scaffold and staging deployment setup
```

If your local branch is still `master`, rename it to `main`:

```bash
git branch -M main
```

Add your GitHub remote and push:

```bash
git remote add origin git@github.com:<org-or-user>/epi-engine.git
git push -u origin main
```

## Current Scope

- FastAPI backend
- Next.js frontend
- ClickHouse SQL schema
- ingestion, scoring, and clustering worker modules
- synthetic/de-identified dev data only

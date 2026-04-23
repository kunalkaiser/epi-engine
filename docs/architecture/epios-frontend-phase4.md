# EpiOS Frontend Phase 4

Phase 4 upgrades `apps/web` from a small dashboard shell into an enterprise frontend OS layer aligned with Phase 2/3 backend capabilities.

## Frontend Information Architecture

Top-level routes (all request-time dynamic):

- `/` - Command Center
- `/disease-explorer`
- `/incidence-prevalence`
- `/determinants-analysis`
- `/indication-prioritizer`
- `/simulation-lab`
- `/compare-scenarios`
- `/data-quality-center`
- `/ingestion-run-center`
- `/audit-viewer`
- `/methodology-center`
- `/health-diagnostics`
- `/admin-tenant-settings`

## Shell and Navigation

- `components/app-shell.tsx` provides:
  - persistent enterprise navigation
  - tenant/role/backend/data-quality context badges
  - runtime status banner
  - role-aware module gating in nav

## Data Access Model

- Web calls backend only through server-side proxy: `app/api/backend/[...path]/route.ts`.
- Proxy forwards authorization from incoming header when present.
- Proxy falls back to server runtime `API_AUTH_TOKEN` when needed.
- No client-side `NEXT_PUBLIC_API_AUTH_TOKEN` usage.
- API client lives in `lib/api.ts` with typed response mappers and error normalization.

## Simulation UX Flow

- `simulation-lab`:
  - submit asynchronous run (`POST /simulation/run`)
  - poll/list run history (`GET /simulation/runs`)
  - fetch result details (`GET /simulation/results/{id}`)
  - cancel queued/running run (`POST /simulation/runs/{id}/cancel`)
- `compare-scenarios`:
  - select 2-5 runs
  - request comparison (`POST /simulation/compare`)
  - render assumption deltas and score spread

## Explainability and Traceability Surfaces

- Determinants page exposes relationship type labels:
  - `descriptive`
  - `associative`
  - `causal_hypothesis`
- Methodology center renders scoring/determinants/simulation metadata payloads.
- Simulation results expose trace IDs, uncertainty bounds, and assumptions snapshot.

## Operational Surfaces

- Data Quality Center: status, severity, rule versions, measured timestamps.
- Ingestion Run Center: source, status, records processed/inserted/rejected.
- Audit Viewer: tenant-scoped activity list.
- Health Diagnostics: frontend/backend/auth/ready/runtime snapshots.

## Aggregate-Only Posture

- UI uses aggregate analytics endpoints only.
- No patient-level drill-down routes or widgets were introduced.
- Patient-level export remains blocked by backend policy.

## Manual Validation

1. Set web runtime env:
   - `API_BASE_URL`
   - `API_AUTH_TOKEN`
2. Start stack (`docker compose up --build`) or run api/web locally.
3. Open web app and verify:
   - nav modules render
   - role gating hides unauthorized modules
   - simulation run submission returns a run and status updates
   - comparison page renders delta output
   - data quality/ingestion/audit pages render live responses or connected-empty states
   - diagnostics page shows backend and auth status

# EpiOS Target Architecture Gap Analysis

## 1. Current Repository Inventory

Implemented and runnable today:

- `apps/api` FastAPI API with auth/RBAC, aggregate endpoints, scoring routes, health/readiness, audit hooks, debug/runtime endpoints.
- `apps/web` Next.js App Router frontend with live request-time API integration, backend proxy, debug panel, loading/empty/error states.
- `apps/worker` ingestion and clustering pipelines, plus runtime worker loop entrypoint.
- `infra/sql` ClickHouse schema/migrations for dimensions, aggregate facts, staging tables, and enterprise aggregate extensions.
- `docker-compose.yml` + `docker-compose.staging.yml` for local and staging topology.
- `.github/workflows/staging.yml` protected-environment staging deployment pipeline scaffold with build/test/package/deploy/verify stages.
- `tests/` unit/integration-style tests for API behavior, RBAC/auth, repository queries, scoring, runtime assumptions, ingestion, and worker runtime.

## 2. Current vs Target Mapping

### A. Landscape Assessment
- `diseases/incidence/prevalence` endpoints: implemented.
- mortality endpoint: implemented and repository-backed.
- confidence/freshness indicators: partially implemented (`/data-quality` summary only).
- geography/time filters + pagination: implemented.

### B. Determinants Analysis
- determinants endpoint with explicit relationship labels (descriptive/associative/causal_hypothesis): implemented baseline.
- configurable modeling and causal workflows: not yet implemented.

### C. Indication Prioritization
- ranked/top indication endpoints with decomposition-capable model outputs: implemented baseline.
- tenant-specific weighting profiles and persistent scoring run audit trails: partially implemented (static defaults, limited persistence).

### D. Simulation / Scenario Analysis
- simulation run/results endpoints: implemented baseline.
- durable simulation run store and scenario diff workflows: partially implemented (schema available, service path not fully persisted yet).

### E. Decision Traceability
- endpoint-level audit events and debug visibility: implemented baseline.
- full lineage chain (source -> model -> run -> export): partially implemented.

### F. Enterprise Platform Capabilities
- RBAC and aggregate-only guardrails: implemented baseline.
- multi-tenant isolation: placeholder only (`tenant_id=default`).
- observability: structured logs + health/readiness/metrics baseline; distributed tracing not yet implemented.
- admin console: not yet implemented.

## 3. Highest-Impact Gaps (Ranked)

1. **Tenant isolation and config persistence**  
   Tenant model, scoped configuration, and per-tenant policies are not yet end-to-end.

2. **Durable operational state**  
   Simulation/audit/data-quality/lineage persistence is still mixed between runtime memory and ClickHouse tables.

3. **Determinants + simulation engine depth**  
   Current outputs are constrained baselines, not yet full methodology-grade model workflows.

4. **Operational hardening depth**  
   Metrics/tracing/SLO-oriented monitoring and runbook coverage need expansion.

5. **Cloud deployment assets**  
   `infra/k8s`, `infra/terraform`, and monitoring stacks are still scaffolds.

## 4. Implementation Phases

### Phase 1 (Completed in current pass)
- establish shared runtime boundaries and explicit gap analysis.
- add enterprise aggregate schema extensions.
- route mortality through repository-backed data access.
- replace worker sleep stub with real worker loop entrypoint.

### Phase 2
- persist simulation outputs to `simulation_run_results`.
- persist ingestion run summaries to `ingestion_runs`.
- surface data-quality checks from `data_quality_results`.

### Phase 3
- tenant metadata model + scoped role policies + config registry.
- per-tenant scoring profiles and methodology versioning.

### Phase 4
- determinants modeling framework with explicit association vs causal pipelines.
- scenario comparison engine and reproducible assumptions registry.

### Phase 5
- production infrastructure assets (k8s/terraform/monitoring) and full operations runbooks.

## 5. Guardrails

- Aggregate-first outputs remain default and enforced.
- No patient-level UI drill-down in standard product routes.
- Development synthetic data remains explicitly dev-only.
- Secrets remain server-side and operator-managed outside repo code.

# EpiOS Backend Phase 2 Hardening

This phase implements durable persistence and tenant-scoped access for simulation runs, ingestion runs, and data-quality results.

## What Was Added

## Durable persistence tables

Migration: `infra/sql/005_phase2_persistence_and_tenant.sql`

- `simulation_runs`
- `simulation_run_items`
- `ingestion_runs_v2`
- `data_quality_results_v2`

All tables are tenant-scoped and append/update-safe using `ReplacingMergeTree(updated_at)` where lifecycle updates are required.

## API surface updates

- `GET /simulation/runs`
- `POST /simulation/run` (now persistent lifecycle-backed)
- `GET /simulation/results/{id}` (reads durable store)
- `GET /admin/ingestion-runs`
- `GET /admin/ingestion-runs/{id}`
- `GET /data-quality` (persistent read path)
- `GET /data-quality/{id}`
- `GET /admin/data-quality-runs`

## Tenant enforcement

- Tenant is resolved from bearer token claims (`tenant_id` or `tid`).
- In non-development environments, missing tenant claim is rejected with typed `401`.
- Tenant override is allowed only for `admin`/`operations` via `X-Tenant-ID`.
- Tenant propagates through API -> service -> repository filters and writes.

## Methodology metadata hardening

Determinants and simulation outputs now include structured methodology metadata:

- method name
- methodology version
- assumptions summary
- data inputs summary
- confidence summary
- causal labeling policy
- generation timestamp

These metadata fields are explicitly descriptive and do not claim unsupported causal validity.

## Worker integration

`apps/worker/ingestion.py` now supports durable ingestion-run lifecycle persistence via `IngestionRunStore` protocol and `ClickHouseIngestionRunStore`.

## Operational notes

If ClickHouse is unavailable, simulation/ingestion/data-quality persistent endpoints fail fast rather than silently using in-memory placeholders.

## Apply order

1. `infra/sql/001_init_schema.sql`
2. `infra/sql/002_staging_tables.sql`
3. `infra/sql/004_enterprise_aggregate_extensions.sql`
4. `infra/sql/005_phase2_persistence_and_tenant.sql`

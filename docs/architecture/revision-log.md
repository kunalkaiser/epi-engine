# Master Revision Log

Last updated: 2026-04-23

## Baseline Validation Run

Executed from repo root:

```bash
python3 -m pytest tests -q
npm --prefix apps/web run test:node
npm --prefix apps/web run build
```

Results:

- Backend tests: `89 passed`, `1 failed` (initial baseline before P0 fix)
- Frontend node env tests: `2 passed`
- Frontend build: `passed`

Failure detail:

- `tests/test_ingestion.py::test_ingest_rejects_non_synthetic_sources`
  - Expected error message pattern: `synthetic data sources`
  - Actual message: `unsupported source_kind: production`
  - Cause: ingestion source adapter hardening changed validation semantics from a synthetic-only gate to a supported-source-kind gate.

## Current Revision Status

P0 and P1 are complete. Current full-suite baseline is green:

- Backend tests: `97 passed`
- Frontend node env tests: `2 passed`
- Frontend build: `passed`

## Prioritized Punch List

### P0 (completed)

1. Aligned ingestion negative-path test with current adapter contract.
   - `tests/test_ingestion.py` now asserts `unsupported source_kind` behavior.

### P1 (completed)

1. Added explicit ingestion entrypoint coverage for all supported source kinds:
   - `synthetic`, `ehr_aggregate`, `claims_aggregate`, `registry_aggregate`, `genomic_summary`, `benchmark_reference`, `literature_metadata`.
2. Added deterministic unsupported-source regression assertion:
   - exact error text validated for unsupported source kind.

### P2 (completed)

1. Aligned wording in worker/docs to separate:
   - "supported source kind" (runtime contract)
   - "synthetic/dev-only data policy" (environment policy)
2. Added ingestion docs note linking adapter runtime boundaries to policy restrictions by environment:
   - `apps/worker/README.md`
   - `docs/architecture/epios-phase6-scientific-pilot-readiness.md`

## Notes

- Frontend dynamic route/build integrity remains healthy.
- No evidence of client-side secret token leakage in current baseline checks.

## Code-Quality Tranche (API/Platform Boundaries)

Completed:

1. Consolidated duplicated response payload construction in `apps/api/services.py`:
   - pagination helper
   - scoring profile payload helper
   - scoring methodology payload helper
2. Centralized repeated route role sets in `apps/api/main.py` to named constants for policy auditability.
3. Improved query model helper typing in `apps/api/query_models.py` via generic model validation helper.
4. Performed low-risk platform cleanup:
   - removed unused imports
   - normalized data-quality row mapper naming
   - reduced duplicate data-quality repository fetch calls in `apps/api/platform_services.py`.

Post-tranche validation:

- `python3 -m pytest tests -q` -> `97 passed`
- `npm --prefix apps/web run test:node` -> `2 passed`
- `npm --prefix apps/web run build` -> passed

## API Contract Normalization Tranche

Completed:

1. Added typed response model for simulation cancel endpoint:
   - `SimulationRunCancelResponse`
   - `POST /simulation/runs/{run_id}/cancel` now declares explicit `response_model`.
2. Added explicit query validation constraints for decision memo endpoint:
   - `region` length constraints
   - `limit` bounds (`1..100`)
   - `profile_id` length constraints
3. Added regression test for invalid decision memo query values.

Post-tranche validation:

- `python3 -m pytest tests/test_platform_endpoints.py tests/test_api_endpoints.py -q` -> `32 passed`
- `python3 -m pytest tests -q` -> `98 passed`
- `npm --prefix apps/web run test:node` -> `2 passed`
- `npm --prefix apps/web run build` -> passed

## Test Architecture Cleanup Tranche

Completed:

1. Added shared auth/token test utilities:
   - `auth_test_utils.py`
2. Removed duplicated JWT encoding/header helpers from:
   - `tests/test_api_endpoints.py`
   - `tests/test_platform_endpoints.py`
   - `tests/test_tenant_enforcement.py`
3. Kept local wrapper functions where useful for test readability while centralizing crypto/claim construction logic.

Post-tranche validation:

- `python3 -m pytest tests/test_api_endpoints.py tests/test_platform_endpoints.py tests/test_tenant_enforcement.py -q` -> `34 passed`
- `python3 -m pytest tests -q` -> `98 passed`
- `npm --prefix apps/web run test:node` -> `2 passed`
- `npm --prefix apps/web run build` -> passed

# EpiOS Phase 6: Scientific Rigor and Pilot Readiness

Phase 6 hardens scientific trust, data integration boundaries, score governance, and pilot-facing operating clarity without weakening aggregate-only posture.

## 1. Scientific Rigor and Classification Guardrails

Implemented:

- Determinants and simulation outputs carry explicit result classification labels:
  - `descriptive`
  - `associative`
  - `causal_hypothesis`
  - `scenario_projection`
- Methodology metadata now includes:
  - method and version
  - assumptions summary and assumptions registry
  - data inputs and input limitations
  - confidence and uncertainty semantics
  - causal labeling policy
  - caveats
- Simulation result rows include caveats and classification metadata.

Guardrail:

- No endpoint in this phase upgrades associative or scenario outputs to causal certainty.
- Causal language remains constrained to hypothesis labeling unless a dedicated causal workflow is present.

## 2. Data Integration Maturity Boundaries

Implemented adapter interfaces in `apps/worker/source_adapters.py` for:

- `synthetic`
- `ehr_aggregate`
- `claims_aggregate`
- `registry_aggregate`
- `genomic_summary`
- `benchmark_reference`
- `literature_metadata`

Each adapter emits:

- normalized row payloads
- `source_system`
- provenance metadata
- freshness timestamp

Ingestion integration:

- `apps/worker/ingestion.py` now routes all supported source kinds through adapter boundaries.
- Live enterprise connectors remain external dependencies and operator-provided.

Runtime vs policy clarification:

- Runtime contract: ingestion accepts only adapter-registered source kinds and rejects unknown values with `unsupported source_kind`.
- Environment policy: `synthetic` is intended for development/test; staging/production should use enterprise adapter kinds and operator-managed connectors.

## 3. Scoring Transparency and Governance

Implemented profile registry in `apps/api/scoring_profiles.py`:

- `default_v1`
- `equity_focus_v1`
- `burden_focus_v1`

Scoring responses now include:

- scoring profile id/version
- methodology version
- confidence label
- classification
- input provenance summary
- limitations/caveats
- factor-level evidence classification and caveat fields

Endpoints supporting profile governance:

- `/indications/top?profile_id=...`
- `/indications/ranked?profile_id=...`

## 4. Pilot Mode and Trust Surfaces

Pilot mode settings:

- `PILOT_MODE_ENABLED`
- `PILOT_MODE_LABEL`

Endpoints:

- `GET /pilot/config`
- `GET /reports/decision-memo`
- `GET /reports/simulation/{run_id}/decision-memo`

Behavior:

- Pilot mode is explicit and externally visible.
- Aggregate-only restrictions remain intact.
- Decision memo outputs are aggregate-safe and include caveats.

## 5. Frontend Trust and Explainability Surfaces

Frontend now surfaces:

- scoring profile and methodology summary in prioritization view
- decision memo summary in prioritization workflow
- pilot mode and auth attachment diagnostics in runtime health page
- structured methodology display instead of raw JSON-only blobs

## 6. Operator-Owned External Dependencies

Still required outside repo code:

- live EHR/claims/registry/genomic connectors and credentials
- cloud storage and artifact retention policy
- production secrets and rotation policies
- Cloudflare Access/IdP group policy enforcement

## 7. Validation Commands

From repo root:

```bash
python3 -m pytest tests/test_platform_endpoints.py tests/test_scoring.py tests/test_source_adapters.py -q
python3 -m pytest tests/test_worker_ingestion_persistence.py tests/test_settings.py -q
npm --prefix apps/web run test:node
npm --prefix apps/web run build
```

# EpiOS Phase 3: Intelligence Layer Hardening

Phase 3 hardens simulation, determinants, explainability, and traceability.

## Async simulation architecture

- `POST /simulation/run` now enqueues a run and returns immediately with `run_id` in `queued` state.
- Worker loop (`apps/worker/worker.py`) processes queued runs via `process_queued_simulation_jobs`.
- Lifecycle states:
  - `queued`
  - `running`
  - `succeeded`
  - `failed`
  - `cancelled`
- Retry behavior:
  - each run tracks `attempt_count` and `max_attempts`
  - failed runs requeue until `max_attempts` is reached
- Traceability:
  - `simulation_run_events` records lifecycle events
  - result rows include uncertainty bounds, driver list, score inputs, and `trace_id`

## Simulation engine

Module: `apps/api/simulation_engine.py`

Supported scenario transforms:
- `subpopulation_targeting`
- `regional_expansion`
- `trial_feasibility`
- `weighting_change`

Engine output per indication:
- baseline score
- simulated score
- delta
- uncertainty low/high
- outcome drivers
- score input snapshot
- trace ID

## Determinants layer updates

Determinants output now computes grouped aggregate signals with explicit output labels:
- descriptive
- associative
- causal_hypothesis

Metadata includes method name/version, assumptions summary, input summary, confidence summary, and causal labeling policy.

## Explainability + decision traceability

Scoring and simulation outputs provide:
- factor-level contribution drivers
- scenario assumptions
- methodology metadata
- run lifecycle metadata (status, attempts, timestamps)
- run event history persisted in `simulation_run_events`

## Scenario comparison

Endpoint: `POST /simulation/compare`

Compares up to 5 runs and returns:
- assumption deltas across runs
- per-indication score spread and run-specific scores

## New SQL migration

- `infra/sql/006_phase3_intelligence_async_simulation.sql`
  - extends simulation tables with retry and traceability fields
  - creates `simulation_run_events`

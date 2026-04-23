USE epi_engine;

-- Phase 3 extends simulation persistence for async execution, retries, and traceability.

ALTER TABLE simulation_runs
    ADD COLUMN IF NOT EXISTS attempt_count UInt8 DEFAULT 0;

ALTER TABLE simulation_runs
    ADD COLUMN IF NOT EXISTS max_attempts UInt8 DEFAULT 2;

ALTER TABLE simulation_run_items
    ADD COLUMN IF NOT EXISTS uncertainty_low Float64 DEFAULT 0;

ALTER TABLE simulation_run_items
    ADD COLUMN IF NOT EXISTS uncertainty_high Float64 DEFAULT 0;

ALTER TABLE simulation_run_items
    ADD COLUMN IF NOT EXISTS outcome_drivers_json String DEFAULT '[]';

ALTER TABLE simulation_run_items
    ADD COLUMN IF NOT EXISTS score_inputs_json String DEFAULT '{}';

ALTER TABLE simulation_run_items
    ADD COLUMN IF NOT EXISTS trace_id String DEFAULT '';

CREATE TABLE IF NOT EXISTS simulation_run_events
(
    event_id String,
    run_id String,
    tenant_id LowCardinality(String),
    event_type LowCardinality(String),
    detail_json String,
    created_at DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(created_at)
ORDER BY (tenant_id, run_id, created_at, event_id);

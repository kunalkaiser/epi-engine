-- EPI Engine — Postgres (Supabase) platform/write-path schema (Phase 2)
-- Port of infra/sql/005 + 006 (simulation persistence, data quality, ingestion runs).
-- Key change from ClickHouse: simulation_runs is a MUTABLE single row per (tenant_id,
-- run_id) with a primary key, so status transitions are real UPDATEs instead of the
-- ReplacingMergeTree append-and-collapse pattern. The full transition history is still
-- preserved in simulation_run_events. Types mapped as in 001 (String->TEXT, UInt*->INT,
-- Float64->DOUBLE PRECISION, DateTime->TIMESTAMPTZ, LowCardinality(String)->TEXT).

CREATE SCHEMA IF NOT EXISTS epi_engine;
SET search_path TO epi_engine, public;

-- simulation_runs — one mutable row per run (created once, UPDATEd in place).
CREATE TABLE IF NOT EXISTS simulation_runs (
    run_id          TEXT NOT NULL,
    tenant_id       TEXT NOT NULL,
    status          TEXT NOT NULL,
    scenario_type   TEXT NOT NULL,
    region_code     TEXT NOT NULL DEFAULT '',
    created_by      TEXT NOT NULL,
    trigger_source  TEXT NOT NULL,
    assumptions_json TEXT NOT NULL,
    methodology_json TEXT NOT NULL,
    result_summary  TEXT NOT NULL DEFAULT '',
    artifact_ref    TEXT NOT NULL DEFAULT '',
    error_message   TEXT NOT NULL DEFAULT '',
    attempt_count   INTEGER NOT NULL DEFAULT 0,
    max_attempts    INTEGER NOT NULL DEFAULT 2,
    created_at      TIMESTAMPTZ NOT NULL,
    updated_at      TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (tenant_id, run_id)
);
CREATE INDEX IF NOT EXISTS ix_simruns_status ON simulation_runs (status, created_at);

-- simulation_run_items — result rows per run/indication (rewritten per run on save).
CREATE TABLE IF NOT EXISTS simulation_run_items (
    run_id          TEXT NOT NULL,
    tenant_id       TEXT NOT NULL,
    indication_id   TEXT NOT NULL,
    indication_name TEXT NOT NULL,
    baseline_score  DOUBLE PRECISION NOT NULL,
    simulated_score DOUBLE PRECISION NOT NULL,
    score_delta     DOUBLE PRECISION NOT NULL,
    uncertainty_low  DOUBLE PRECISION NOT NULL DEFAULT 0,
    uncertainty_high DOUBLE PRECISION NOT NULL DEFAULT 0,
    outcome_drivers_json TEXT NOT NULL DEFAULT '[]',
    score_inputs_json    TEXT NOT NULL DEFAULT '{}',
    trace_id        TEXT NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_simitems_run ON simulation_run_items (tenant_id, run_id);

-- simulation_run_events — append-only lifecycle/audit log.
CREATE TABLE IF NOT EXISTS simulation_run_events (
    event_id    TEXT PRIMARY KEY,
    run_id      TEXT NOT NULL,
    tenant_id   TEXT NOT NULL,
    event_type  TEXT NOT NULL,
    detail_json TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_simevents_run ON simulation_run_events (tenant_id, run_id, created_at);

-- data_quality_results_v2 — append-only (each result_id is a distinct measurement).
CREATE TABLE IF NOT EXISTS data_quality_results_v2 (
    result_id   TEXT PRIMARY KEY,
    tenant_id   TEXT NOT NULL,
    domain      TEXT NOT NULL,
    check_type  TEXT NOT NULL,
    severity    TEXT NOT NULL,
    status      TEXT NOT NULL,
    summary_metrics_json    TEXT NOT NULL,
    failing_dimensions_json TEXT NOT NULL,
    thresholds_json TEXT NOT NULL,
    rules_version   TEXT NOT NULL,
    ingestion_run_id TEXT NOT NULL DEFAULT '',
    measured_at  TIMESTAMPTZ NOT NULL,
    created_by   TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL,
    updated_at   TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_dq_domain ON data_quality_results_v2 (tenant_id, domain, measured_at);

-- ingestion_runs_v2 — written by the worker (apps/worker), read here. Append-and-collapse
-- model preserved (latest row per run_id via DISTINCT ON at read time). Empty until the
-- worker's ingestion writes are also ported to Postgres (separate task).
CREATE TABLE IF NOT EXISTS ingestion_runs_v2 (
    run_id          TEXT NOT NULL,
    tenant_id       TEXT NOT NULL,
    dataset_name    TEXT NOT NULL,
    source_system   TEXT NOT NULL,
    trigger_source  TEXT NOT NULL,
    status          TEXT NOT NULL,
    source_ref      TEXT NOT NULL DEFAULT '',
    records_processed BIGINT NOT NULL DEFAULT 0,
    records_inserted  BIGINT NOT NULL DEFAULT 0,
    records_updated   BIGINT NOT NULL DEFAULT 0,
    records_rejected  BIGINT NOT NULL DEFAULT 0,
    validation_summary_json TEXT NOT NULL DEFAULT '{}',
    error_summary_json      TEXT NOT NULL DEFAULT '{}',
    freshness_metric TEXT NOT NULL DEFAULT '',
    provenance_ref   TEXT NOT NULL DEFAULT '',
    artifact_ref     TEXT NOT NULL DEFAULT '',
    created_by       TEXT NOT NULL,
    started_at       TIMESTAMPTZ NOT NULL,
    completed_at     TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL,
    updated_at       TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_ingest_run ON ingestion_runs_v2 (tenant_id, run_id, updated_at);

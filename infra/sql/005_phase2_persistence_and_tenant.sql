USE epi_engine;

-- simulation_runs
-- Durable simulation run lifecycle with tenant scoping and methodology metadata.
CREATE TABLE IF NOT EXISTS simulation_runs
(
    run_id String,
    tenant_id LowCardinality(String),
    status LowCardinality(String),
    scenario_type LowCardinality(String),
    region_code LowCardinality(String),
    created_by String,
    trigger_source LowCardinality(String),
    assumptions_json String,
    methodology_json String,
    result_summary String,
    artifact_ref String,
    error_message String,
    created_at DateTime,
    updated_at DateTime
)
ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYYYYMM(created_at)
ORDER BY (tenant_id, run_id, updated_at);

-- simulation_run_items
-- Durable simulation result rows by run and indication.
CREATE TABLE IF NOT EXISTS simulation_run_items
(
    run_id String,
    tenant_id LowCardinality(String),
    indication_id String,
    indication_name String,
    baseline_score Float64,
    simulated_score Float64,
    score_delta Float64,
    created_at DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(created_at)
ORDER BY (tenant_id, run_id, indication_id);

-- ingestion_runs_v2
-- Durable ingestion lifecycle and quality summary with tenant scoping.
CREATE TABLE IF NOT EXISTS ingestion_runs_v2
(
    run_id String,
    tenant_id LowCardinality(String),
    dataset_name LowCardinality(String),
    source_system LowCardinality(String),
    trigger_source LowCardinality(String),
    status LowCardinality(String),
    source_ref String,
    records_processed UInt64,
    records_inserted UInt64,
    records_updated UInt64,
    records_rejected UInt64,
    validation_summary_json String,
    error_summary_json String,
    freshness_metric String,
    provenance_ref String,
    artifact_ref String,
    created_by String,
    started_at DateTime,
    completed_at Nullable(DateTime),
    created_at DateTime,
    updated_at DateTime
)
ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYYYYMM(started_at)
ORDER BY (tenant_id, dataset_name, run_id, updated_at);

-- data_quality_results_v2
-- Durable data quality outputs for trend and history analysis.
CREATE TABLE IF NOT EXISTS data_quality_results_v2
(
    result_id String,
    tenant_id LowCardinality(String),
    domain LowCardinality(String),
    check_type LowCardinality(String),
    severity LowCardinality(String),
    status LowCardinality(String),
    summary_metrics_json String,
    failing_dimensions_json String,
    thresholds_json String,
    rules_version String,
    ingestion_run_id String,
    measured_at DateTime,
    created_by String,
    created_at DateTime,
    updated_at DateTime
)
ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYYYYMM(measured_at)
ORDER BY (tenant_id, domain, check_type, measured_at, result_id);

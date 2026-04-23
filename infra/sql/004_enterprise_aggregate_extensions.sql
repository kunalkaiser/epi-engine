USE epi_engine;

-- mortality_facts
-- Aggregate mortality metrics aligned with incidence/prevalence query patterns.
CREATE TABLE IF NOT EXISTS mortality_facts
(
    disease_id String,
    disease_name String,
    region_code LowCardinality(String),
    population_segment LowCardinality(String),
    metric_year UInt16,
    deaths UInt64,
    population UInt64,
    mortality_per_100k Float64,
    source_name String,
    loaded_at DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY metric_year
ORDER BY (disease_id, region_code, population_segment, metric_year);

-- determinants_summary_facts
-- Aggregate determinants features and modeled contribution summaries by disease/region/time.
CREATE TABLE IF NOT EXISTS determinants_summary_facts
(
    disease_id String,
    disease_name String,
    region_code LowCardinality(String),
    metric_year UInt16,
    clinical_signal Float64,
    biomarker_signal Float64,
    social_signal Float64,
    environmental_signal Float64,
    confidence_level LowCardinality(String),
    methodology_tag LowCardinality(String),
    source_name String,
    loaded_at DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY metric_year
ORDER BY (disease_id, region_code, metric_year);

-- simulation_run_results
-- Aggregate-only simulation run snapshots for reproducibility and audit traceability.
CREATE TABLE IF NOT EXISTS simulation_run_results
(
    run_id String,
    scenario_type LowCardinality(String),
    tenant_id LowCardinality(String),
    region_code Nullable(LowCardinality(String)),
    indication_id String,
    indication_name String,
    baseline_score Float64,
    simulated_score Float64,
    score_delta Float64,
    assumptions_json String,
    created_by String,
    created_at DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(created_at)
ORDER BY (run_id, indication_id, created_at);

-- ingestion_runs
-- Ingestion execution metadata for lineage, quality, and operations visibility.
CREATE TABLE IF NOT EXISTS ingestion_runs
(
    run_id String,
    dataset_name LowCardinality(String),
    source_kind LowCardinality(String),
    source_ref String,
    status LowCardinality(String),
    total_rows UInt64,
    valid_rows UInt64,
    invalid_rows UInt64,
    error_counts_json String,
    started_at DateTime,
    completed_at Nullable(DateTime),
    created_at DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(started_at)
ORDER BY (dataset_name, started_at, run_id);

-- data_quality_results
-- Data quality and freshness check outputs by domain for operational readiness.
CREATE TABLE IF NOT EXISTS data_quality_results
(
    check_id String,
    domain LowCardinality(String),
    status LowCardinality(String),
    severity LowCardinality(String),
    detail String,
    measured_at DateTime,
    created_at DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(measured_at)
ORDER BY (domain, measured_at, check_id);

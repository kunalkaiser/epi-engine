USE epi_engine;

-- staging_patient_summary
-- Raw validated patient summary rows awaiting downstream transformation.
CREATE TABLE IF NOT EXISTS staging_patient_summary
(
    population_label String,
    age_band LowCardinality(String),
    sex LowCardinality(String),
    count UInt64,
    ingested_at DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ingested_at)
ORDER BY (population_label, age_band, sex, ingested_at);

-- staging_diagnosis
-- Raw validated diagnosis rows awaiting dimension loading.
CREATE TABLE IF NOT EXISTS staging_diagnosis
(
    code String,
    system LowCardinality(String),
    label String,
    prevalence_per_100k Nullable(Float64),
    ingested_at DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ingested_at)
ORDER BY (system, code, ingested_at);

-- staging_medication
-- Raw validated medication rows awaiting dimension loading.
CREATE TABLE IF NOT EXISTS staging_medication
(
    name String,
    route LowCardinality(String),
    status LowCardinality(String),
    competition_class LowCardinality(String),
    ingested_at DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ingested_at)
ORDER BY (competition_class, name, ingested_at);

-- staging_lab_result
-- Raw validated lab result rows awaiting normalization.
CREATE TABLE IF NOT EXISTS staging_lab_result
(
    test_code String,
    test_name String,
    value Float64,
    unit LowCardinality(String),
    reference_low Nullable(Float64),
    reference_high Nullable(Float64),
    interpretation LowCardinality(String),
    collected_on Date,
    ingested_at DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(collected_on)
ORDER BY (test_code, collected_on, interpretation, ingested_at);

-- staging_encounter
-- Raw validated encounter rows awaiting fact loading.
CREATE TABLE IF NOT EXISTS staging_encounter
(
    encounter_type LowCardinality(String),
    region_code LowCardinality(String),
    period_start Date,
    period_end Date,
    aggregate_count UInt64,
    ingested_at DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(period_start)
ORDER BY (region_code, encounter_type, period_start, ingested_at);

-- staging_incidence_aggregate
-- Raw validated incidence rows for aggregate analytics ingestion.
CREATE TABLE IF NOT EXISTS staging_incidence_aggregate
(
    disease_id String,
    disease_name String,
    region_code LowCardinality(String),
    year UInt16,
    incident_cases UInt64,
    population UInt64,
    incidence_per_100k Float64,
    ingested_at DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY year
ORDER BY (disease_id, region_code, year, ingested_at);

-- staging_prevalence_aggregate
-- Raw validated prevalence rows for aggregate analytics ingestion.
CREATE TABLE IF NOT EXISTS staging_prevalence_aggregate
(
    disease_id String,
    disease_name String,
    region_code LowCardinality(String),
    year UInt16,
    prevalent_cases UInt64,
    population UInt64,
    prevalence_per_100k Float64,
    ingested_at DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY year
ORDER BY (disease_id, region_code, year, ingested_at);

-- staging_indication_score
-- Raw validated prioritization score rows awaiting reporting use.
CREATE TABLE IF NOT EXISTS staging_indication_score
(
    indication_id String,
    indication_name String,
    incidence_score Float64,
    unmet_need_score Float64,
    market_size_score Float64,
    competition_score Float64,
    total_score Float64,
    ingested_at DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ingested_at)
ORDER BY (indication_id, total_score, ingested_at);

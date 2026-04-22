CREATE DATABASE IF NOT EXISTS epi_engine;

USE epi_engine;

-- dim_patient
-- De-identified patient dimension used only for aggregate cohort analysis.
-- Stores coarse demographic attributes and never includes PHI fields.
CREATE TABLE IF NOT EXISTS dim_patient
(
    patient_key UUID,
    synthetic_source_id String,
    birth_year UInt16,
    sex LowCardinality(String),
    region_code LowCardinality(String),
    created_at DateTime DEFAULT now()
)
ENGINE = MergeTree
ORDER BY (region_code, sex, birth_year, patient_key);

-- dim_diagnosis
-- Diagnosis reference dimension for normalized disease and indication analysis.
CREATE TABLE IF NOT EXISTS dim_diagnosis
(
    diagnosis_key UUID,
    diagnosis_code String,
    coding_system LowCardinality(String),
    diagnosis_name String,
    disease_area LowCardinality(String),
    created_at DateTime DEFAULT now()
)
ENGINE = MergeTree
ORDER BY (coding_system, diagnosis_code, diagnosis_key);

-- dim_medication
-- Medication reference dimension used for competition and treatment landscape summaries.
CREATE TABLE IF NOT EXISTS dim_medication
(
    medication_key UUID,
    medication_name String,
    route LowCardinality(String),
    status LowCardinality(String),
    competition_class LowCardinality(String),
    created_at DateTime DEFAULT now()
)
ENGINE = MergeTree
ORDER BY (competition_class, medication_name, medication_key);

-- dim_lab_test
-- Lab test reference dimension for cohort-level biomarker and test utilization analysis.
CREATE TABLE IF NOT EXISTS dim_lab_test
(
    lab_test_key UUID,
    test_code String,
    coding_system LowCardinality(String),
    test_name String,
    standard_unit LowCardinality(String),
    created_at DateTime DEFAULT now()
)
ENGINE = MergeTree
ORDER BY (coding_system, test_code, lab_test_key);

-- fct_patient_encounter
-- Encounter fact table for synthetic or de-identified patient activity.
-- Partitioned by encounter month for efficient time-bounded filtering.
CREATE TABLE IF NOT EXISTS fct_patient_encounter
(
    encounter_key UUID,
    patient_key UUID,
    diagnosis_key UUID,
    medication_key UUID,
    lab_test_key UUID,
    encounter_date Date,
    encounter_type LowCardinality(String),
    region_code LowCardinality(String),
    lab_value Nullable(Float64),
    lab_unit Nullable(String),
    created_at DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(encounter_date)
ORDER BY (encounter_date, region_code, diagnosis_key, patient_key, encounter_key);

-- incidence_facts
-- Aggregate incidence metrics for disease explorer and indication prioritization.
-- Partitioned by year to support trend analysis and bulk reloads.
CREATE TABLE IF NOT EXISTS incidence_facts
(
    disease_id String,
    disease_name String,
    region_code LowCardinality(String),
    population_segment LowCardinality(String),
    metric_year UInt16,
    incident_cases UInt64,
    population UInt64,
    incidence_per_100k Float64,
    source_name String,
    loaded_at DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY metric_year
ORDER BY (disease_id, region_code, population_segment, metric_year);

-- prevalence_facts
-- Aggregate prevalence metrics for disease explorer and prioritization models.
-- Partitioned by year to keep reads efficient for time-series slices.
CREATE TABLE IF NOT EXISTS prevalence_facts
(
    disease_id String,
    disease_name String,
    region_code LowCardinality(String),
    population_segment LowCardinality(String),
    metric_year UInt16,
    prevalent_cases UInt64,
    population UInt64,
    prevalence_per_100k Float64,
    source_name String,
    loaded_at DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY metric_year
ORDER BY (disease_id, region_code, population_segment, metric_year);

-- indication_profile_facts
-- Aggregate-safe indication inputs used for prioritization scoring.
-- Stores only indication-level factor scores, never patient-level data.
CREATE TABLE IF NOT EXISTS indication_profile_facts
(
    indication_id String,
    indication_name String,
    region_code LowCardinality(String),
    incidence Float64,
    prevalence Float64,
    unmet_need Float64,
    market_size Float64,
    competition_penalty Float64,
    equity_score Float64,
    loaded_at DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(loaded_at)
ORDER BY (region_code, indication_name, indication_id);

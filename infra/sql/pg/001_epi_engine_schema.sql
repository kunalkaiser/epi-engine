-- EPI Engine — Postgres (Supabase) read-path schema
-- Port of infra/sql/001_init_schema.sql + 004 fact tables for the BigQuery/Supabase
-- migration (Phase 1: read path only). Engines/ORDER BY/PARTITION clauses from the
-- ClickHouse DDL are dropped (Postgres uses indexes); types are mapped:
--   String -> TEXT, LowCardinality(String) -> TEXT, UInt16/UInt64 -> INTEGER/BIGINT,
--   Float64 -> DOUBLE PRECISION, DateTime -> TIMESTAMPTZ, Nullable(X) -> nullable column.
-- Namespaced in its own schema so it does not collide with the shared Supabase app tables.

CREATE SCHEMA IF NOT EXISTS epi_engine;
SET search_path TO epi_engine, public;

-- incidence_facts — aggregate incidence metrics for the disease explorer.
CREATE TABLE IF NOT EXISTS incidence_facts (
    disease_id          TEXT NOT NULL,
    disease_name        TEXT NOT NULL,
    region_code         TEXT NOT NULL,
    population_segment  TEXT NOT NULL DEFAULT 'all_ages',
    metric_year         INTEGER NOT NULL,
    incident_cases      BIGINT NOT NULL,
    population          BIGINT NOT NULL,
    incidence_per_100k  DOUBLE PRECISION NOT NULL,
    source_name         TEXT NOT NULL,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_incidence_disease_region_year
    ON incidence_facts (disease_id, region_code, metric_year);

-- prevalence_facts — aggregate prevalence metrics for the disease explorer.
CREATE TABLE IF NOT EXISTS prevalence_facts (
    disease_id          TEXT NOT NULL,
    disease_name        TEXT NOT NULL,
    region_code         TEXT NOT NULL,
    population_segment  TEXT NOT NULL DEFAULT 'all_ages',
    metric_year         INTEGER NOT NULL,
    prevalent_cases     BIGINT NOT NULL,
    population          BIGINT NOT NULL,
    prevalence_per_100k DOUBLE PRECISION NOT NULL,
    source_name         TEXT NOT NULL,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_prevalence_disease_region_year
    ON prevalence_facts (disease_id, region_code, metric_year);

-- mortality_facts — aggregate mortality metrics (read path /mortality).
CREATE TABLE IF NOT EXISTS mortality_facts (
    disease_id          TEXT NOT NULL,
    disease_name        TEXT NOT NULL,
    region_code         TEXT NOT NULL,
    population_segment  TEXT NOT NULL DEFAULT 'all_ages',
    metric_year         INTEGER NOT NULL,
    deaths              BIGINT NOT NULL,
    population          BIGINT NOT NULL,
    mortality_per_100k  DOUBLE PRECISION NOT NULL,
    source_name         TEXT NOT NULL,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_mortality_disease_region_year
    ON mortality_facts (disease_id, region_code, metric_year);

-- indication_profile_facts — aggregate-safe indication inputs for ranking (/indications/ranked).
CREATE TABLE IF NOT EXISTS indication_profile_facts (
    indication_id       TEXT NOT NULL,
    indication_name     TEXT NOT NULL,
    region_code         TEXT NOT NULL,
    incidence           DOUBLE PRECISION NOT NULL,
    prevalence          DOUBLE PRECISION NOT NULL,
    unmet_need          DOUBLE PRECISION NOT NULL,
    market_size         DOUBLE PRECISION NOT NULL,
    competition_penalty DOUBLE PRECISION NOT NULL,
    equity_score        DOUBLE PRECISION NOT NULL,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_indication_region
    ON indication_profile_facts (region_code, indication_name);

-- determinants_summary_facts — aggregate determinants features (read path /determinants).
CREATE TABLE IF NOT EXISTS determinants_summary_facts (
    disease_id          TEXT NOT NULL,
    disease_name        TEXT NOT NULL,
    region_code         TEXT NOT NULL,
    metric_year         INTEGER NOT NULL,
    clinical_signal     DOUBLE PRECISION NOT NULL,
    biomarker_signal    DOUBLE PRECISION NOT NULL,
    social_signal       DOUBLE PRECISION NOT NULL,
    environmental_signal DOUBLE PRECISION NOT NULL,
    confidence_level    TEXT NOT NULL,
    methodology_tag     TEXT NOT NULL,
    source_name         TEXT NOT NULL,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_determinants_disease_region_year
    ON determinants_summary_facts (disease_id, region_code, metric_year);

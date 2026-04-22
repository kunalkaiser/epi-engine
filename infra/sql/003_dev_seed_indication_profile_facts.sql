USE epi_engine;

-- Development-only synthetic seed for indication_profile_facts.
-- This keeps ranked indication endpoints backed by ClickHouse rows in local dev.
INSERT INTO indication_profile_facts
(
    indication_id,
    indication_name,
    region_code,
    incidence,
    prevalence,
    unmet_need,
    market_size,
    competition_penalty,
    equity_score
)
SELECT
    seed.indication_id,
    seed.indication_name,
    seed.region_code,
    seed.incidence,
    seed.prevalence,
    seed.unmet_need,
    seed.market_size,
    seed.competition_penalty,
    seed.equity_score
FROM
(
    SELECT
        't2d-us' AS indication_id,
        'Type 2 diabetes' AS indication_name,
        'US' AS region_code,
        84.0 AS incidence,
        78.0 AS prevalence,
        61.0 AS unmet_need,
        88.0 AS market_size,
        58.0 AS competition_penalty,
        38.0 AS equity_score
    UNION ALL
    SELECT
        'copd-us',
        'Chronic obstructive pulmonary disease',
        'US',
        67.0,
        73.0,
        74.0,
        72.0,
        44.0,
        49.0
    UNION ALL
    SELECT
        'ckd-us-ca',
        'Chronic kidney disease',
        'US-CA',
        52.0,
        69.0,
        82.0,
        64.0,
        31.0,
        71.0
) AS seed
WHERE (SELECT count() FROM indication_profile_facts) = 0;

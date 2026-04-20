DROP MATERIALIZED VIEW IF EXISTS core.mv_district_year_funding_performance;

CREATE MATERIALIZED VIEW core.mv_district_year_funding_performance AS
WITH district_aggregates AS (
    SELECT
        e.year::smallint AS year,
        d.district_key,
        d.district_name,
        COUNT(DISTINCT s.school_key)::integer AS school_count,
        AVG(e.per_pupil_total_raw)::double precision AS avg_per_pupil_funding,
        AVG(o.ach_all)::double precision AS avg_achievement
    FROM core.dim_district d
    JOIN core.dim_school s
        ON s.district_key = d.district_key
    LEFT JOIN core.fact_edunomics e
        ON e.school_key = s.school_key
    LEFT JOIN core.fact_school_outcomes_wide o
        ON o.school_key = s.school_key
        AND o.year = e.year
    WHERE e.year IS NOT NULL
    GROUP BY e.year, d.district_key, d.district_name
)
SELECT
    year,
    district_key,
    district_name,
    school_count,
    avg_per_pupil_funding,
    avg_achievement,
    DENSE_RANK() OVER (
        PARTITION BY year
        ORDER BY avg_per_pupil_funding DESC NULLS LAST
    )::integer AS funding_rank
FROM district_aggregates;

CREATE UNIQUE INDEX uq_mv_district_year_funding_performance
    ON core.mv_district_year_funding_performance (year, district_key);

CREATE INDEX idx_mv_district_year_funding_performance_rank
    ON core.mv_district_year_funding_performance (year, funding_rank, district_key);

CREATE INDEX IF NOT EXISTS idx_core_fact_edunomics_year_school
    ON core.fact_edunomics (year, school_key);

CREATE INDEX IF NOT EXISTS idx_core_fact_school_outcomes_wide_year_school
    ON core.fact_school_outcomes_wide (year, school_key);

-- For recurring refresh jobs:
-- REFRESH MATERIALIZED VIEW CONCURRENTLY core.mv_district_year_funding_performance;

CREATE MATERIALIZED VIEW IF NOT EXISTS platinum.mv_district_year_funding_performance AS
WITH district_aggregates AS (
    SELECT
        d.district_key,
        d.district_name,
        e.year,
        COUNT(DISTINCT s.school_key)::integer AS school_count,
        AVG(e.per_pupil_total_raw)::double precision AS avg_per_pupil_funding,
        AVG(o.ach_all)::double precision AS avg_achievement
    FROM gold.dim_district d
    JOIN gold.dim_school s
      ON s.district_key = d.district_key
    LEFT JOIN gold.fact_edunomics e
      ON e.school_key = s.school_key
    LEFT JOIN gold.fact_school_outcomes_wide o
      ON o.school_key = s.school_key
     AND o.year = e.year
    WHERE e.year IS NOT NULL
    GROUP BY d.district_key, d.district_name, e.year
)
SELECT
    district_key,
    district_name,
    year,
    school_count,
    avg_per_pupil_funding,
    avg_achievement,
    DENSE_RANK() OVER (
        PARTITION BY year
        ORDER BY avg_per_pupil_funding DESC NULLS LAST
    )::integer AS funding_rank
FROM district_aggregates;

CREATE UNIQUE INDEX IF NOT EXISTS uq_mv_district_year_funding_performance
    ON platinum.mv_district_year_funding_performance (year, district_key);

CREATE INDEX IF NOT EXISTS idx_mv_district_year_funding_performance_rank
    ON platinum.mv_district_year_funding_performance (year, funding_rank, district_key);

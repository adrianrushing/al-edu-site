DROP MATERIALIZED VIEW IF EXISTS core.mv_fact_accountability_all_pivot;

CREATE MATERIALIZED VIEW core.mv_fact_accountability_all_pivot AS
WITH filtered AS (
    SELECT
        fa.school_key,
        fa.year,
        fa.indicator,
        fa.score,
        fa._created_at,
        fa._updated_at
    FROM core.fact_accountability fa
    WHERE fa.grade = 'All Grades'
      AND fa.gender = 'All Gender'
      AND fa.race = 'All Race'
      AND fa.ethnicity = 'All Ethnicity'
      AND fa.sub_population = 'All SubPopulation'
),
pivoted AS (
    SELECT
        f.school_key,
        f.year,
        MAX(
            CASE
                WHEN f.indicator IN ('Student Achievement', 'Academic Achievement')
                    THEN f.score
                ELSE NULL
            END
        ) AS achievement,
        MAX(CASE WHEN f.indicator = 'Graduation Rate' THEN f.score ELSE NULL END)
            AS graduation_rate,
        MAX(CASE WHEN f.indicator = 'Academic Growth' THEN f.score ELSE NULL END)
            AS academic_growth,
        MAX(CASE WHEN f.indicator = 'Chronic Absenteeism' THEN f.score ELSE NULL END)
            AS absenteeism,
        MAX(
            CASE
                WHEN f.indicator = 'College and Career Readiness' THEN f.score
                ELSE NULL
            END
        ) AS ccr,
        MAX(
            CASE
                WHEN f.indicator = 'Progress in English Language Proficiency' THEN f.score
                ELSE NULL
            END
        ) AS elp,
        MAX(f._created_at) AS _created_at,
        MAX(f._updated_at) AS _updated_at
    FROM filtered f
    GROUP BY f.school_key, f.year
)
SELECT
    p.school_key,
    p.year,
    d.dist_name,
    d.school_name,
    p.achievement,
    p.graduation_rate,
    p.academic_growth,
    p.absenteeism,
    p.ccr,
    p.elp,
    p._created_at,
    p._updated_at
FROM pivoted p
LEFT JOIN core.dim_school_info d
  ON d.school_key = p.school_key
 AND d.school_year_start = p.year;

CREATE UNIQUE INDEX uq_mv_fact_accountability_all_pivot_school_year
    ON core.mv_fact_accountability_all_pivot (school_key, year);

CREATE INDEX idx_mv_fact_accountability_all_pivot_year_school
    ON core.mv_fact_accountability_all_pivot (year, school_key);

-- For recurring refresh jobs:
-- REFRESH MATERIALIZED VIEW CONCURRENTLY core.mv_fact_accountability_all_pivot;

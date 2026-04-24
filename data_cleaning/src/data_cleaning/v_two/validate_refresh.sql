\set ON_ERROR_STOP on

SELECT now() AS checked_at;

WITH sandbox AS (
    SELECT 'dim_school_info' AS dataset, MIN(school_year_start)::int AS min_year, MAX(school_year_start)::int AS max_year, COUNT(*)::bigint AS rows_total
    FROM sandbox.dim_school_info_review
    UNION ALL
    SELECT 'accountability', MIN(year)::int, MAX(year)::int, COUNT(*)::bigint FROM sandbox.fact_accountability_review
    UNION ALL
    SELECT 'student_demographics', MIN(year)::int, MAX(year)::int, COUNT(*)::bigint FROM sandbox.fact_student_demographics_long_review
    UNION ALL
    SELECT 'teacher_demographics', MIN(year)::int, MAX(year)::int, COUNT(*)::bigint FROM sandbox.fact_teacher_demographics_long_review
    UNION ALL
    SELECT 'teacher_experience', MIN(year)::int, MAX(year)::int, COUNT(*)::bigint FROM sandbox.fact_teacher_experience_review
    UNION ALL
    SELECT 'teacher_effectiveness', MIN(year)::int, MAX(year)::int, COUNT(*)::bigint FROM sandbox.fact_teacher_effectiveness_review
    UNION ALL
    SELECT 'edunomics', MIN(year)::int, MAX(year)::int, COUNT(*)::bigint FROM sandbox.fact_edunomics_review
),
core AS (
    SELECT 'dim_school_info' AS dataset, MIN(school_year_start)::int AS min_year, MAX(school_year_start)::int AS max_year, COUNT(*)::bigint AS rows_total
    FROM core.dim_school_info
    UNION ALL
    SELECT 'accountability', MIN(year)::int, MAX(year)::int, COUNT(*)::bigint FROM core.fact_accountability
    UNION ALL
    SELECT 'student_demographics', MIN(year)::int, MAX(year)::int, COUNT(*)::bigint FROM core.fact_student_demographics
    UNION ALL
    SELECT 'teacher_demographics', MIN(year)::int, MAX(year)::int, COUNT(*)::bigint FROM core.fact_teacher_demographics
    UNION ALL
    SELECT 'teacher_experience', MIN(year)::int, MAX(year)::int, COUNT(*)::bigint FROM core.fact_teacher_experience
    UNION ALL
    SELECT 'teacher_effectiveness', MIN(year)::int, MAX(year)::int, COUNT(*)::bigint FROM core.fact_teacher_effectiveness
    UNION ALL
    SELECT 'edunomics', MIN(year)::int, MAX(year)::int, COUNT(*)::bigint FROM core.fact_edunomics
)
SELECT
    s.dataset,
    s.min_year AS sandbox_min_year,
    s.max_year AS sandbox_max_year,
    s.rows_total AS sandbox_rows,
    c.min_year AS core_min_year,
    c.max_year AS core_max_year,
    c.rows_total AS core_rows,
    (s.max_year - c.max_year) AS max_year_gap
FROM sandbox s
JOIN core c USING (dataset)
ORDER BY s.dataset;

WITH rows_2025 AS (
    SELECT 'accountability' AS dataset,
           (SELECT COUNT(*)::bigint FROM sandbox.fact_accountability_review WHERE year = 2025) AS sandbox_rows_2025,
           (SELECT COUNT(*)::bigint FROM core.fact_accountability WHERE year = 2025) AS core_rows_2025
    UNION ALL
    SELECT 'student_demographics',
           (SELECT COUNT(*)::bigint FROM sandbox.fact_student_demographics_long_review WHERE year = 2025),
           (SELECT COUNT(*)::bigint FROM core.fact_student_demographics WHERE year = 2025)
    UNION ALL
    SELECT 'teacher_demographics',
           (SELECT COUNT(*)::bigint FROM sandbox.fact_teacher_demographics_long_review WHERE year = 2025),
           (SELECT COUNT(*)::bigint FROM core.fact_teacher_demographics WHERE year = 2025)
    UNION ALL
    SELECT 'teacher_experience',
           (SELECT COUNT(*)::bigint FROM sandbox.fact_teacher_experience_review WHERE year = 2025),
           (SELECT COUNT(*)::bigint FROM core.fact_teacher_experience WHERE year = 2025)
)
SELECT * FROM rows_2025 ORDER BY dataset;

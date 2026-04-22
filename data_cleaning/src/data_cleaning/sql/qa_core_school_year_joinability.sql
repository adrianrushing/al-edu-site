-- QA checks for school-year profile joinability and usefulness.
-- Run after core_load_review_to_core.sql and core_load_geo_to_core.sql.

-- 1) Constraint inventory for core schema tables used in school-year joins.
SELECT
    tc.table_schema,
    tc.table_name,
    tc.constraint_name,
    tc.constraint_type,
    kcu.column_name,
    ccu.table_schema AS foreign_table_schema,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints tc
LEFT JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name
 AND tc.table_schema = kcu.table_schema
 AND tc.table_name = kcu.table_name
LEFT JOIN information_schema.constraint_column_usage ccu
  ON tc.constraint_name = ccu.constraint_name
 AND tc.table_schema = ccu.table_schema
WHERE tc.table_schema = 'core'
  AND tc.table_name IN (
      'dim_school_info',
      'dim_school',
      'dim_district',
      'dim_state',
      'fact_school_outcomes_wide',
      'fact_edunomics',
      'fact_teacher_effectiveness',
      'fact_teacher_experience',
      'bridge_school_geo_county',
      'fact_geo_opportunity_county',
      'fact_geo_population_county'
  )
ORDER BY tc.table_name, tc.constraint_type, tc.constraint_name, kcu.ordinal_position;

-- 2) Uniqueness checks at expected join grain.
SELECT
    'core.dim_school_info' AS table_name,
    count(*) AS row_count,
    count(DISTINCT (school_key, school_year_start)) AS grain_distinct_count,
    count(*) - count(DISTINCT (school_key, school_year_start)) AS duplicate_rows
FROM core.dim_school_info
UNION ALL
SELECT
    'core.fact_school_outcomes_wide',
    count(*),
    count(DISTINCT (school_key, year)),
    count(*) - count(DISTINCT (school_key, year))
FROM core.fact_school_outcomes_wide
UNION ALL
SELECT
    'core.fact_edunomics',
    count(*),
    count(DISTINCT (school_key, year)),
    count(*) - count(DISTINCT (school_key, year))
FROM core.fact_edunomics
UNION ALL
SELECT
    'core.fact_teacher_effectiveness',
    count(*),
    count(DISTINCT (school_key, year)),
    count(*) - count(DISTINCT (school_key, year))
FROM core.fact_teacher_effectiveness
UNION ALL
SELECT
    'core.bridge_school_geo_county',
    count(*),
    count(DISTINCT (school_key, school_year_start)),
    count(*) - count(DISTINCT (school_key, school_year_start))
FROM core.bridge_school_geo_county
UNION ALL
SELECT
    'core.fact_geo_opportunity_county',
    count(*),
    count(DISTINCT (county_fips, year, metric_code, norm_scope)),
    count(*) - count(DISTINCT (county_fips, year, metric_code, norm_scope))
FROM core.fact_geo_opportunity_county
UNION ALL
SELECT
    'core.fact_geo_population_county',
    count(*),
    count(DISTINCT (county_fips, year, population_group)),
    count(*) - count(DISTINCT (county_fips, year, population_group))
FROM core.fact_geo_population_county;

-- 3) Fanout check for teacher experience before and after All SubPopulation filter.
SELECT
    year,
    school_key,
    count(*) AS row_count
FROM core.fact_teacher_experience
GROUP BY year, school_key
HAVING count(*) > 1
ORDER BY row_count DESC, year DESC
LIMIT 25;

SELECT
    year,
    school_key,
    count(*) AS row_count
FROM core.fact_teacher_experience
WHERE sub_population = 'All SubPopulation'
GROUP BY year, school_key
HAVING count(*) > 1
ORDER BY row_count DESC, year DESC
LIMIT 25;

-- 4) Year overlap across all major join inputs.
SELECT 'dim_school_info' AS source, min(school_year_start) AS min_year, max(school_year_start) AS max_year
FROM core.dim_school_info
UNION ALL
SELECT 'fact_school_outcomes_wide', min(year), max(year)
FROM core.fact_school_outcomes_wide
UNION ALL
SELECT 'fact_edunomics', min(year), max(year)
FROM core.fact_edunomics
UNION ALL
SELECT 'fact_teacher_effectiveness', min(year), max(year)
FROM core.fact_teacher_effectiveness
UNION ALL
SELECT 'fact_teacher_experience', min(year), max(year)
FROM core.fact_teacher_experience
UNION ALL
SELECT 'bridge_school_geo_county', min(school_year_start), max(school_year_start)
FROM core.bridge_school_geo_county
UNION ALL
SELECT 'fact_geo_opportunity_county', min(year), max(year)
FROM core.fact_geo_opportunity_county
UNION ALL
SELECT 'fact_geo_population_county', min(year), max(year)
FROM core.fact_geo_population_county;

-- 5) Join-hit diagnostics by year (school-year grain preservation).
WITH base AS (
    SELECT school_key, school_year_start AS year
    FROM core.dim_school_info
),
teacher_all AS (
    SELECT school_key, year
    FROM core.fact_teacher_experience
    WHERE sub_population = 'All SubPopulation'
    GROUP BY school_key, year
)
SELECT
    b.year,
    count(*) AS school_year_rows,
    count(o.school_key) AS outcomes_rows,
    count(e.school_key) AS edunomics_rows,
    count(te.school_key) AS teacher_effectiveness_rows,
    count(tx.school_key) AS teacher_experience_all_rows,
    count(g.school_key) AS county_bridge_rows,
    count(g.school_key) FILTER (WHERE g.county_fips IS NOT NULL) AS county_fips_nonnull_rows,
    round(100.0 * count(o.school_key) / nullif(count(*), 0), 2) AS outcomes_hit_pct,
    round(100.0 * count(e.school_key) / nullif(count(*), 0), 2) AS edunomics_hit_pct,
    round(100.0 * count(tx.school_key) / nullif(count(*), 0), 2) AS teacher_experience_hit_pct,
    round(100.0 * count(g.school_key) FILTER (WHERE g.county_fips IS NOT NULL) / nullif(count(*), 0), 2) AS county_resolved_pct
FROM base b
LEFT JOIN core.fact_school_outcomes_wide o
  ON o.school_key = b.school_key
 AND o.year = b.year
LEFT JOIN core.fact_edunomics e
  ON e.school_key = b.school_key
 AND e.year = b.year
LEFT JOIN core.fact_teacher_effectiveness te
  ON te.school_key = b.school_key
 AND te.year = b.year
LEFT JOIN teacher_all tx
  ON tx.school_key = b.school_key
 AND tx.year = b.year
LEFT JOIN core.bridge_school_geo_county g
  ON g.school_key = b.school_key
 AND g.school_year_start = b.year
GROUP BY b.year
ORDER BY b.year;

-- 6) County linkage quality and strict-null reasons.
SELECT
    coalesce(strict_null_reason, 'MATCHED') AS mapping_status,
    count(*) AS row_count
FROM core.bridge_school_geo_county
GROUP BY coalesce(strict_null_reason, 'MATCHED')
ORDER BY row_count DESC;

SELECT
    school_year_start AS year,
    coalesce(strict_null_reason, 'MATCHED') AS mapping_status,
    count(*) AS row_count
FROM core.bridge_school_geo_county
GROUP BY school_year_start, coalesce(strict_null_reason, 'MATCHED')
ORDER BY school_year_start, row_count DESC;

-- 7) Usefulness checks for modeling fields in full profile grain.
WITH joined AS (
    SELECT
        i.school_key,
        i.school_year_start AS year,
        o.ach_all,
        o.ppe,
        e.per_pupil_total_raw,
        e.nces_poverty,
        tx.exp_rate,
        g.county_fips,
        go.opportunity_score_avg AS county_coi_stt_score,
        gp.population_count AS county_population_total
    FROM core.dim_school_info i
    LEFT JOIN core.fact_school_outcomes_wide o
      ON o.school_key = i.school_key
     AND o.year = i.school_year_start
    LEFT JOIN core.fact_edunomics e
      ON e.school_key = i.school_key
     AND e.year = i.school_year_start
    LEFT JOIN (
        SELECT school_key, year, avg(exp_rate)::double precision AS exp_rate
        FROM core.fact_teacher_experience
        WHERE sub_population = 'All SubPopulation'
        GROUP BY school_key, year
    ) tx
      ON tx.school_key = i.school_key
     AND tx.year = i.school_year_start
    LEFT JOIN core.bridge_school_geo_county g
      ON g.school_key = i.school_key
     AND g.school_year_start = i.school_year_start
    LEFT JOIN core.fact_geo_opportunity_county go
      ON go.county_fips = g.county_fips
     AND go.year = i.school_year_start
     AND go.metric_code = 'COI'
     AND go.norm_scope = 'stt'
    LEFT JOIN core.fact_geo_population_county gp
      ON gp.county_fips = g.county_fips
     AND gp.year = i.school_year_start
     AND gp.population_group = 'total'
)
SELECT
    year,
    count(*) AS row_count,
    round(100.0 * avg(CASE WHEN ach_all IS NOT NULL THEN 1 ELSE 0 END), 2) AS ach_all_nonnull_pct,
    round(100.0 * avg(CASE WHEN per_pupil_total_raw IS NOT NULL THEN 1 ELSE 0 END), 2) AS per_pupil_total_raw_nonnull_pct,
    round(100.0 * avg(CASE WHEN nces_poverty IS NOT NULL THEN 1 ELSE 0 END), 2) AS nces_poverty_nonnull_pct,
    round(100.0 * avg(CASE WHEN exp_rate IS NOT NULL THEN 1 ELSE 0 END), 2) AS exp_rate_nonnull_pct,
    round(100.0 * avg(CASE WHEN county_fips IS NOT NULL THEN 1 ELSE 0 END), 2) AS county_fips_nonnull_pct,
    round(100.0 * avg(CASE WHEN county_coi_stt_score IS NOT NULL THEN 1 ELSE 0 END), 2) AS county_coi_stt_nonnull_pct,
    round(100.0 * avg(CASE WHEN county_population_total IS NOT NULL THEN 1 ELSE 0 END), 2) AS county_population_total_nonnull_pct
FROM joined
GROUP BY year
ORDER BY year;

-- 8) District-year sample sufficiency for district-aware modeling.
WITH district_year_counts AS (
    SELECT
        d.district_key,
        i.school_year_start AS year,
        count(*)::integer AS school_count
    FROM core.dim_school_info i
    JOIN core.dim_school s
      ON s.school_key = i.school_key
    JOIN core.dim_district d
      ON d.district_key = s.district_key
    GROUP BY d.district_key, i.school_year_start
)
SELECT
    year,
    count(*) AS district_year_rows,
    count(*) FILTER (WHERE school_count >= 2) AS district_year_rows_ge_2,
    count(*) FILTER (WHERE school_count >= 3) AS district_year_rows_ge_3,
    min(school_count) AS min_school_count,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY school_count) AS median_school_count,
    max(school_count) AS max_school_count
FROM district_year_counts
GROUP BY year
ORDER BY year;

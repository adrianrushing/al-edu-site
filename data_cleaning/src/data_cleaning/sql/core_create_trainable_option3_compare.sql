-- Build option-3 trainable enrichment views with both COI variants:
-- 1) as-of district COI average (leakage-safe)
-- 2) all-years district COI average (coverage/stability)
--
-- Run after:
-- - core_load_review_to_core.sql
-- - core_load_geo_to_core.sql
-- - core_create_school_year_profiles.sql

BEGIN;

DROP VIEW IF EXISTS core.vw_school_year_full_profile_trainable_option3;
DROP VIEW IF EXISTS core.vw_district_coi_features;
DROP VIEW IF EXISTS core.vw_district_county_weights;

CREATE VIEW core.vw_district_county_weights AS
WITH district_county_counts AS (
    SELECT
        s.district_key,
        b.county_fips,
        count(*)::double precision AS mapped_school_year_count
    FROM core.bridge_school_geo_county b
    JOIN core.dim_school s
      ON s.school_key = b.school_key
    WHERE b.county_fips IS NOT NULL
      AND b.strict_null_reason IS NULL
    GROUP BY s.district_key, b.county_fips
),
district_totals AS (
    SELECT
        district_key,
        sum(mapped_school_year_count) AS mapped_school_year_total
    FROM district_county_counts
    GROUP BY district_key
)
SELECT
    c.district_key,
    c.county_fips,
    c.mapped_school_year_count,
    t.mapped_school_year_total,
    c.mapped_school_year_count / nullif(t.mapped_school_year_total, 0) AS county_weight
FROM district_county_counts c
JOIN district_totals t
  ON t.district_key = c.district_key;

CREATE VIEW core.vw_district_coi_features AS
WITH county_coi AS (
    SELECT
        county_fips,
        year,
        opportunity_score_avg
    FROM core.fact_geo_opportunity_county
    WHERE metric_code = 'COI'
      AND norm_scope = 'stt'
      AND opportunity_score_avg IS NOT NULL
),
district_years AS (
    SELECT DISTINCT
        s.district_key,
        i.school_year_start AS year
    FROM core.dim_school_info i
    JOIN core.dim_school s
      ON s.school_key = i.school_key
),
district_county_all_years AS (
    SELECT
        w.district_key,
        w.county_fips,
        w.county_weight,
        avg(c.opportunity_score_avg)::double precision AS county_coi_all_years_avg,
        count(*)::integer AS county_coi_all_years_obs_count,
        min(c.year)::smallint AS county_coi_all_years_min_year,
        max(c.year)::smallint AS county_coi_all_years_max_year
    FROM core.vw_district_county_weights w
    LEFT JOIN county_coi c
      ON c.county_fips = w.county_fips
    GROUP BY w.district_key, w.county_fips, w.county_weight
),
district_all_years AS (
    SELECT
        district_key,
        sum(county_weight * county_coi_all_years_avg)
            / nullif(sum(CASE WHEN county_coi_all_years_avg IS NOT NULL THEN county_weight END), 0)
            AS district_coi_all_years_avg,
        sum(county_coi_all_years_obs_count)::integer AS district_coi_all_years_obs_count,
        min(county_coi_all_years_min_year)::smallint AS district_coi_all_years_min_year,
        max(county_coi_all_years_max_year)::smallint AS district_coi_all_years_max_year
    FROM district_county_all_years
    GROUP BY district_key
),
district_county_asof AS (
    SELECT
        dy.district_key,
        dy.year,
        w.county_fips,
        w.county_weight,
        avg(c.opportunity_score_avg)::double precision AS county_coi_asof_avg,
        count(c.opportunity_score_avg)::integer AS county_coi_asof_obs_count,
        max(c.year)::smallint AS county_coi_asof_latest_year
    FROM district_years dy
    JOIN core.vw_district_county_weights w
      ON w.district_key = dy.district_key
    LEFT JOIN county_coi c
      ON c.county_fips = w.county_fips
     AND c.year <= dy.year
    GROUP BY dy.district_key, dy.year, w.county_fips, w.county_weight
),
district_asof AS (
    SELECT
        district_key,
        year,
        sum(county_weight * county_coi_asof_avg)
            / nullif(sum(CASE WHEN county_coi_asof_avg IS NOT NULL THEN county_weight END), 0)
            AS district_coi_asof_avg,
        sum(county_coi_asof_obs_count)::integer AS district_coi_asof_obs_count,
        max(county_coi_asof_latest_year)::smallint AS district_coi_asof_latest_year
    FROM district_county_asof
    GROUP BY district_key, year
)
SELECT
    dy.district_key,
    dy.year,
    da.district_coi_asof_avg,
    da.district_coi_asof_obs_count,
    da.district_coi_asof_latest_year,
    CASE
        WHEN da.district_coi_asof_latest_year IS NULL THEN NULL
        ELSE dy.year - da.district_coi_asof_latest_year
    END::integer AS district_coi_asof_lag_years,
    ay.district_coi_all_years_avg,
    ay.district_coi_all_years_obs_count,
    ay.district_coi_all_years_min_year,
    ay.district_coi_all_years_max_year,
    (da.district_coi_asof_avg IS NOT NULL) AS has_district_coi_asof,
    (ay.district_coi_all_years_avg IS NOT NULL) AS has_district_coi_all_years
FROM district_years dy
LEFT JOIN district_asof da
  ON da.district_key = dy.district_key
 AND da.year = dy.year
LEFT JOIN district_all_years ay
  ON ay.district_key = dy.district_key;

CREATE VIEW core.vw_school_year_full_profile_trainable_option3 AS
WITH base AS (
    SELECT
        p.*,
        dcf.district_coi_asof_avg,
        dcf.district_coi_asof_obs_count,
        dcf.district_coi_asof_latest_year,
        dcf.district_coi_asof_lag_years,
        dcf.district_coi_all_years_avg,
        dcf.district_coi_all_years_obs_count,
        dcf.district_coi_all_years_min_year,
        dcf.district_coi_all_years_max_year,
        dcf.has_district_coi_asof,
        dcf.has_district_coi_all_years
    FROM core.vw_school_year_full_profile p
    LEFT JOIN core.vw_district_coi_features dcf
      ON dcf.district_key = p.district_key
     AND dcf.year = p.year
),
edunomics_asof AS (
    SELECT
        target_school_key AS school_key,
        target_year AS year,
        source_year AS edunomics_asof_year,
        per_pupil_total_raw AS per_pupil_total_raw_asof,
        nces_poverty AS nces_poverty_asof,
        nces_freelunch AS nces_freelunch_asof,
        target_year - source_year AS edunomics_asof_lag_years
    FROM (
        SELECT
            b.school_key AS target_school_key,
            b.year AS target_year,
            e.year AS source_year,
            e.per_pupil_total_raw,
            e.nces_poverty,
            e.nces_freelunch,
            row_number() OVER (
                PARTITION BY b.school_key, b.year
                ORDER BY e.year DESC
            ) AS rn
        FROM (
            SELECT DISTINCT school_key, year
            FROM base
        ) b
        JOIN core.fact_edunomics e
          ON e.school_key = b.school_key
         AND e.year <= b.year
        WHERE e.per_pupil_total_raw IS NOT NULL
          AND e.nces_poverty IS NOT NULL
          AND e.nces_freelunch IS NOT NULL
    ) ranked
    WHERE rn = 1
)
SELECT
    b.*,
    ea.edunomics_asof_year,
    ea.edunomics_asof_lag_years,
    ea.per_pupil_total_raw_asof,
    ea.nces_poverty_asof,
    ea.nces_freelunch_asof,
    coalesce(b.per_pupil_total_raw, ea.per_pupil_total_raw_asof) AS per_pupil_total_raw_trainable,
    coalesce(b.nces_poverty, ea.nces_poverty_asof) AS nces_poverty_trainable,
    coalesce(b.nces_freelunch, ea.nces_freelunch_asof) AS nces_freelunch_trainable,
    coalesce(b.county_coi_stt_score, b.district_coi_asof_avg) AS coi_option3_asof_feature,
    coalesce(b.county_coi_stt_score, b.district_coi_all_years_avg) AS coi_option3_all_years_feature,
    (b.county_coi_stt_score IS NOT NULL) AS has_temporal_county_coi,
    (b.county_coi_stt_score IS NULL AND b.district_coi_asof_avg IS NOT NULL) AS coi_filled_from_district_asof,
    (b.county_coi_stt_score IS NULL AND b.district_coi_all_years_avg IS NOT NULL) AS coi_filled_from_district_all_years,
    (ea.per_pupil_total_raw_asof IS NOT NULL) AS has_edunomics_asof_fill
FROM base b
LEFT JOIN edunomics_asof ea
  ON ea.school_key = b.school_key
 AND ea.year = b.year;

COMMIT;

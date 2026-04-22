-- Build school-year and district-year profile views in core.
-- Run after core_load_review_to_core.sql and core_load_geo_to_core.sql.

BEGIN;

DROP VIEW IF EXISTS core.vw_school_year_full_profile;
DROP VIEW IF EXISTS core.vw_district_year_profile;
DROP VIEW IF EXISTS core.vw_district_year_features;

CREATE VIEW core.vw_district_year_features AS
WITH teacher_experience_all AS (
    SELECT
        t.school_key,
        t.year,
        count(*)::integer AS teacher_exp_row_count,
        avg(t.total_count)::double precision AS teacher_total_count,
        avg(t.exp_count)::double precision AS teacher_exp_count,
        avg(t.inexp_count)::double precision AS teacher_inexp_count,
        avg(t.exp_rate)::double precision AS exp_rate,
        avg(t.inexp_rate)::double precision AS inexp_rate
    FROM core.fact_teacher_experience t
    WHERE t.sub_population = 'All SubPopulation'
    GROUP BY t.school_key, t.year
),
school_year_base AS (
    SELECT
        i.school_key,
        i.school_year_start AS year,
        s.district_key,
        o.ach_all,
        o.grw_all,
        o.abs_all,
        o.ppe,
        e.per_pupil_total_raw,
        e.nces_poverty,
        e.nces_freelunch,
        tx.exp_rate,
        tx.inexp_rate
    FROM core.dim_school_info i
    JOIN core.dim_school s
      ON s.school_key = i.school_key
    LEFT JOIN core.fact_school_outcomes_wide o
      ON o.school_key = i.school_key
     AND o.year = i.school_year_start
    LEFT JOIN core.fact_edunomics e
      ON e.school_key = i.school_key
     AND e.year = i.school_year_start
    LEFT JOIN teacher_experience_all tx
      ON tx.school_key = i.school_key
     AND tx.year = i.school_year_start
)
SELECT
    b.district_key,
    b.year,
    count(*)::integer AS district_school_count,
    count(*) FILTER (WHERE b.ach_all IS NOT NULL)::integer AS district_ach_observed_count,
    count(*) FILTER (WHERE b.per_pupil_total_raw IS NOT NULL)::integer AS district_funding_observed_count,
    avg(b.ach_all)::double precision AS district_mean_ach_all,
    stddev_samp(b.ach_all)::double precision AS district_sd_ach_all,
    avg(b.grw_all)::double precision AS district_mean_grw_all,
    avg(b.abs_all)::double precision AS district_mean_abs_all,
    avg(b.ppe)::double precision AS district_mean_ppe,
    avg(b.per_pupil_total_raw)::double precision AS district_mean_per_pupil_total_raw,
    stddev_samp(b.per_pupil_total_raw)::double precision AS district_sd_per_pupil_total_raw,
    avg(b.nces_poverty)::double precision AS district_mean_nces_poverty,
    avg(b.nces_freelunch)::double precision AS district_mean_nces_freelunch,
    avg(b.exp_rate)::double precision AS district_mean_exp_rate,
    avg(b.inexp_rate)::double precision AS district_mean_inexp_rate
FROM school_year_base b
GROUP BY b.district_key, b.year;

CREATE VIEW core.vw_school_year_full_profile AS
WITH teacher_experience_all AS (
    SELECT
        t.school_key,
        t.year,
        count(*)::integer AS teacher_exp_row_count,
        avg(t.total_count)::double precision AS teacher_total_count,
        avg(t.exp_count)::double precision AS teacher_exp_count,
        avg(t.inexp_count)::double precision AS teacher_inexp_count,
        avg(t.exp_rate)::double precision AS exp_rate,
        avg(t.inexp_rate)::double precision AS inexp_rate
    FROM core.fact_teacher_experience t
    WHERE t.sub_population = 'All SubPopulation'
    GROUP BY t.school_key, t.year
),
county_opportunity_stt AS (
    SELECT
        g.county_fips,
        g.year,
        max(CASE WHEN g.metric_code = 'COI' AND g.norm_scope = 'stt' THEN g.opportunity_score_avg END) AS county_coi_stt_score,
        max(CASE WHEN g.metric_code = 'COI' AND g.norm_scope = 'stt' THEN g.opportunity_zscore_avg END) AS county_coi_stt_zscore,
        max(CASE WHEN g.metric_code = 'ED' AND g.norm_scope = 'stt' THEN g.opportunity_score_avg END) AS county_ed_stt_score,
        max(CASE WHEN g.metric_code = 'ED' AND g.norm_scope = 'stt' THEN g.opportunity_zscore_avg END) AS county_ed_stt_zscore,
        max(CASE WHEN g.metric_code = 'HE' AND g.norm_scope = 'stt' THEN g.opportunity_score_avg END) AS county_he_stt_score,
        max(CASE WHEN g.metric_code = 'HE' AND g.norm_scope = 'stt' THEN g.opportunity_zscore_avg END) AS county_he_stt_zscore,
        max(CASE WHEN g.metric_code = 'SE' AND g.norm_scope = 'stt' THEN g.opportunity_score_avg END) AS county_se_stt_score,
        max(CASE WHEN g.metric_code = 'SE' AND g.norm_scope = 'stt' THEN g.opportunity_zscore_avg END) AS county_se_stt_zscore,
        max(CASE WHEN g.metric_code = 'COI' AND g.norm_scope = 'stt' THEN g.tract_count END)::integer AS county_coi_stt_tract_count
    FROM core.fact_geo_opportunity_county g
    GROUP BY g.county_fips, g.year
),
county_population AS (
    SELECT
        p.county_fips,
        p.year,
        max(CASE WHEN p.population_group = 'total' THEN p.population_count END) AS county_population_total,
        max(CASE WHEN p.population_group = 'white' THEN p.population_count END) AS county_population_white,
        max(CASE WHEN p.population_group = 'black' THEN p.population_count END) AS county_population_black,
        max(CASE WHEN p.population_group = 'hisp' THEN p.population_count END) AS county_population_hisp,
        max(CASE WHEN p.population_group = 'asian' THEN p.population_count END) AS county_population_asian,
        max(CASE WHEN p.population_group = 'aian' THEN p.population_count END) AS county_population_aian
    FROM core.fact_geo_population_county p
    GROUP BY p.county_fips, p.year
)
SELECT
    i.school_key,
    i.school_year_start AS year,
    i.school_year_label,
    i.school_year_end,
    st.state_key,
    st.state_code,
    st.department_name,
    d.district_key,
    d.district_name,
    d.state_dist_id,
    d.nces_admin_id,
    i.dist_name,
    s.school_name,
    i.state_school_id,
    i.nces_id,
    i.nces_geo_id,
    i.census_id,
    i.nces_locale_key,
    i.nces_locale_type,
    i.nces_locale_subtype,
    i.nces_charter,
    i.nces_magnet,
    i.nces_address,
    i.nces_city,
    i.nces_zip,
    o.ach_all,
    o.grw_all,
    o.abs_all,
    o.coi,
    o.coi_ed,
    o.coi_he,
    o.coi_st,
    o.ppe,
    e.ncesenroll,
    e.gradespan,
    e.level,
    e.enroll_raw,
    e.state_local_per_pupil,
    e.state_local_fund,
    e.nces_fund,
    e.nces_poverty,
    e.title_i_status,
    e.nces_freelunch,
    e.nces_reducedlunch,
    e.per_pupil_nces_raw,
    e.per_pupil_total_raw,
    e.per_pupil_total_norm_nerds,
    e.flag_nerds,
    e.flag_f33,
    te.effectiveness_score AS teacher_effectiveness_score,
    te.atot_completion_rate_designation,
    te.title_i_status AS teacher_effectiveness_title_i_status,
    tx.teacher_exp_row_count,
    tx.teacher_total_count,
    tx.teacher_exp_count,
    tx.teacher_inexp_count,
    tx.exp_rate,
    tx.inexp_rate,
    b.county_fips,
    b.county_name,
    b.match_method,
    b.match_confidence,
    b.strict_null_reason,
    co.county_coi_stt_score,
    co.county_coi_stt_zscore,
    co.county_ed_stt_score,
    co.county_ed_stt_zscore,
    co.county_he_stt_score,
    co.county_he_stt_zscore,
    co.county_se_stt_score,
    co.county_se_stt_zscore,
    co.county_coi_stt_tract_count,
    cp.county_population_total,
    cp.county_population_white,
    cp.county_population_black,
    cp.county_population_hisp,
    cp.county_population_asian,
    cp.county_population_aian,
    CASE
        WHEN cp.county_population_total IS NULL OR cp.county_population_total = 0 THEN NULL
        ELSE cp.county_population_white / cp.county_population_total
    END AS county_pct_white,
    CASE
        WHEN cp.county_population_total IS NULL OR cp.county_population_total = 0 THEN NULL
        ELSE cp.county_population_black / cp.county_population_total
    END AS county_pct_black,
    CASE
        WHEN cp.county_population_total IS NULL OR cp.county_population_total = 0 THEN NULL
        ELSE cp.county_population_hisp / cp.county_population_total
    END AS county_pct_hisp,
    CASE
        WHEN cp.county_population_total IS NULL OR cp.county_population_total = 0 THEN NULL
        ELSE cp.county_population_asian / cp.county_population_total
    END AS county_pct_asian,
    CASE
        WHEN cp.county_population_total IS NULL OR cp.county_population_total = 0 THEN NULL
        ELSE cp.county_population_aian / cp.county_population_total
    END AS county_pct_aian,
    df.district_school_count,
    df.district_ach_observed_count,
    df.district_funding_observed_count,
    df.district_mean_ach_all,
    df.district_sd_ach_all,
    df.district_mean_grw_all,
    df.district_mean_abs_all,
    df.district_mean_ppe,
    df.district_mean_per_pupil_total_raw,
    df.district_sd_per_pupil_total_raw,
    df.district_mean_nces_poverty,
    df.district_mean_nces_freelunch,
    df.district_mean_exp_rate,
    df.district_mean_inexp_rate,
    o.ach_all - df.district_mean_ach_all AS ach_all_minus_district_mean,
    e.per_pupil_total_raw - df.district_mean_per_pupil_total_raw AS per_pupil_total_minus_district_mean,
    e.nces_poverty - df.district_mean_nces_poverty AS nces_poverty_minus_district_mean,
    tx.exp_rate - df.district_mean_exp_rate AS exp_rate_minus_district_mean
FROM core.dim_school_info i
JOIN core.dim_school s
  ON s.school_key = i.school_key
JOIN core.dim_district d
  ON d.district_key = s.district_key
JOIN core.dim_state st
  ON st.state_key = d.state_key
LEFT JOIN core.fact_school_outcomes_wide o
  ON o.school_key = i.school_key
 AND o.year = i.school_year_start
LEFT JOIN core.fact_edunomics e
  ON e.school_key = i.school_key
 AND e.year = i.school_year_start
LEFT JOIN core.fact_teacher_effectiveness te
  ON te.school_key = i.school_key
 AND te.year = i.school_year_start
LEFT JOIN teacher_experience_all tx
  ON tx.school_key = i.school_key
 AND tx.year = i.school_year_start
LEFT JOIN core.bridge_school_geo_county b
  ON b.school_key = i.school_key
 AND b.school_year_start = i.school_year_start
LEFT JOIN county_opportunity_stt co
  ON co.county_fips = b.county_fips
 AND co.year = i.school_year_start
LEFT JOIN county_population cp
  ON cp.county_fips = b.county_fips
 AND cp.year = i.school_year_start
LEFT JOIN core.vw_district_year_features df
  ON df.district_key = s.district_key
 AND df.year = i.school_year_start;

CREATE VIEW core.vw_district_year_profile AS
SELECT
    df.district_key,
    d.state_key,
    st.state_code,
    st.department_name,
    d.district_name,
    d.state_dist_id,
    d.nces_admin_id,
    df.year,
    df.district_school_count,
    df.district_ach_observed_count,
    df.district_funding_observed_count,
    df.district_mean_ach_all,
    df.district_sd_ach_all,
    df.district_mean_grw_all,
    df.district_mean_abs_all,
    df.district_mean_ppe,
    df.district_mean_per_pupil_total_raw,
    df.district_sd_per_pupil_total_raw,
    df.district_mean_nces_poverty,
    df.district_mean_nces_freelunch,
    df.district_mean_exp_rate,
    df.district_mean_inexp_rate
FROM core.vw_district_year_features df
JOIN core.dim_district d
  ON d.district_key = df.district_key
JOIN core.dim_state st
  ON st.state_key = d.state_key;

COMMIT;

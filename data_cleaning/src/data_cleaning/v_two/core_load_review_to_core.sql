\set ON_ERROR_STOP on

BEGIN;

CREATE SCHEMA IF NOT EXISTS core;

CREATE OR REPLACE FUNCTION pg_temp.norm_name(v TEXT)
RETURNS TEXT
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT lower(regexp_replace(trim(coalesce(v, '')), '[[:space:]]+', ' ', 'g'))
$$;

INSERT INTO core.dim_state (
    state_key,
    state_code,
    department_name,
    _created_at,
    _updated_at
)
SELECT
    s.state_key::bigint,
    s.state_code::char(2),
    s.department_name,
    coalesce(s._created_at::timestamptz, now()),
    now()
FROM sandbox.dim_state_review s
ON CONFLICT (state_key) DO UPDATE SET
    state_code = EXCLUDED.state_code,
    department_name = EXCLUDED.department_name,
    _updated_at = now();

INSERT INTO core.dim_district (
    district_key,
    state_key,
    state_code,
    district_name,
    district_name_norm,
    state_dist_id,
    nces_admin_id,
    source_state_dist_id,
    _created_at,
    _updated_at
)
SELECT
    d.district_key::bigint,
    d.state_key::bigint,
    d.state_code::char(2),
    d.district_name,
    d.district_name_norm,
    d.state_dist_id::integer,
    d.nces_admin_id::bigint,
    d.source_state_dist_id,
    coalesce(d._created_at::timestamptz, now()),
    now()
FROM sandbox.dim_district_review d
ON CONFLICT (district_key) DO UPDATE SET
    state_key = EXCLUDED.state_key,
    state_code = EXCLUDED.state_code,
    district_name = EXCLUDED.district_name,
    district_name_norm = EXCLUDED.district_name_norm,
    state_dist_id = EXCLUDED.state_dist_id,
    nces_admin_id = EXCLUDED.nces_admin_id,
    source_state_dist_id = EXCLUDED.source_state_dist_id,
    _updated_at = now();

INSERT INTO core.dim_school (
    school_key,
    district_key,
    state_code,
    school_name,
    school_name_norm,
    state_school_id,
    nces_geo_id,
    census_id,
    nces_id,
    nces_charter,
    nces_magnet,
    nces_address,
    nces_city,
    nces_zip,
    source_state_school_id,
    _created_at,
    _updated_at
)
SELECT
    s.school_key::bigint,
    s.district_key::bigint,
    s.state_code::char(2),
    s.school_name,
    s.school_name_norm,
    s.state_school_id::integer,
    s.nces_geo_id::bigint,
    s.census_id::bigint,
    s.nces_id::bigint,
    s.nces_charter,
    s.nces_magnet,
    s.nces_address,
    s.nces_city,
    s.nces_zip,
    s.source_state_school_id,
    coalesce(s._created_at::timestamptz, now()),
    now()
FROM sandbox.dim_school_review s
ON CONFLICT (school_key) DO UPDATE SET
    district_key = EXCLUDED.district_key,
    state_code = EXCLUDED.state_code,
    school_name = EXCLUDED.school_name,
    school_name_norm = EXCLUDED.school_name_norm,
    state_school_id = EXCLUDED.state_school_id,
    nces_geo_id = EXCLUDED.nces_geo_id,
    census_id = EXCLUDED.census_id,
    nces_id = EXCLUDED.nces_id,
    nces_charter = EXCLUDED.nces_charter,
    nces_magnet = EXCLUDED.nces_magnet,
    nces_address = EXCLUDED.nces_address,
    nces_city = EXCLUDED.nces_city,
    nces_zip = EXCLUDED.nces_zip,
    source_state_school_id = EXCLUDED.source_state_school_id,
    _updated_at = now();

INSERT INTO core.bridge_school_year (
    school_key,
    school_year_label,
    school_year_start,
    school_year_end,
    nces_locale_key,
    nces_locale_type,
    nces_locale_subtype,
    source_nces_locale,
    _source_file,
    _ingested_at,
    _created_at,
    _updated_at
)
SELECT
    b.school_key::bigint,
    b.school_year_label,
    b.school_year_start::smallint,
    b.school_year_end::smallint,
    b.nces_locale_key::smallint,
    b.nces_locale_type,
    b.nces_locale_subtype,
    b.source_nces_locale,
    b._source_file,
    b._ingested_at,
    coalesce(b._created_at::timestamptz, now()),
    now()
FROM sandbox.bridge_school_year_review b
ON CONFLICT (school_key, school_year_start) DO UPDATE SET
    school_year_label = EXCLUDED.school_year_label,
    school_year_end = EXCLUDED.school_year_end,
    nces_locale_key = EXCLUDED.nces_locale_key,
    nces_locale_type = EXCLUDED.nces_locale_type,
    nces_locale_subtype = EXCLUDED.nces_locale_subtype,
    source_nces_locale = EXCLUDED.source_nces_locale,
    _source_file = EXCLUDED._source_file,
    _ingested_at = EXCLUDED._ingested_at,
    _updated_at = now();

INSERT INTO core.dim_school_info (
    school_key,
    school_year_label,
    school_year_start,
    school_year_end,
    state_code,
    state_dist_id,
    state_school_id,
    nces_admin_id,
    nces_geo_id,
    census_id,
    nces_id,
    dist_name,
    school_name,
    nces_locale_key,
    nces_locale_type,
    nces_locale_subtype,
    source_nces_locale,
    nces_charter,
    nces_magnet,
    nces_address,
    nces_city,
    nces_zip,
    _created_at,
    _updated_at
)
SELECT
    s.school_key::bigint,
    s.school_year_label,
    s.school_year_start::smallint,
    s.school_year_end::smallint,
    s.state_code::char(2),
    s.state_dist_id::integer,
    s.state_school_id::integer,
    s.nces_admin_id::bigint,
    s.nces_geo_id::bigint,
    s.census_id::bigint,
    s.nces_id::bigint,
    s.dist_name,
    s.school_name,
    s.nces_locale_key::smallint,
    s.nces_locale_type,
    s.nces_locale_subtype,
    s.source_nces_locale,
    s.nces_charter,
    s.nces_magnet,
    s.nces_address,
    s.nces_city,
    s.nces_zip,
    coalesce(s._created_at::timestamptz, now()),
    now()
FROM sandbox.dim_school_info_review s
ON CONFLICT (school_key, school_year_start) DO UPDATE SET
    school_year_label = EXCLUDED.school_year_label,
    school_year_end = EXCLUDED.school_year_end,
    state_code = EXCLUDED.state_code,
    state_dist_id = EXCLUDED.state_dist_id,
    state_school_id = EXCLUDED.state_school_id,
    nces_admin_id = EXCLUDED.nces_admin_id,
    nces_geo_id = EXCLUDED.nces_geo_id,
    census_id = EXCLUDED.census_id,
    nces_id = EXCLUDED.nces_id,
    dist_name = EXCLUDED.dist_name,
    school_name = EXCLUDED.school_name,
    nces_locale_key = EXCLUDED.nces_locale_key,
    nces_locale_type = EXCLUDED.nces_locale_type,
    nces_locale_subtype = EXCLUDED.nces_locale_subtype,
    source_nces_locale = EXCLUDED.source_nces_locale,
    nces_charter = EXCLUDED.nces_charter,
    nces_magnet = EXCLUDED.nces_magnet,
    nces_address = EXCLUDED.nces_address,
    nces_city = EXCLUDED.nces_city,
    nces_zip = EXCLUDED.nces_zip,
    _updated_at = now();

CREATE TEMP TABLE _school_key_map AS
SELECT
    school_key,
    school_year_start AS year,
    state_dist_id,
    state_school_id,
    pg_temp.norm_name(dist_name) AS dist_name_norm,
    pg_temp.norm_name(school_name) AS school_name_norm
FROM core.dim_school_info;

CREATE INDEX _idx_school_key_map_lookup
    ON _school_key_map (year, dist_name_norm, school_name_norm);

TRUNCATE TABLE
    core.fact_teacher_demographics,
    core.fact_student_demographics,
    core.fact_accountability,
    core.fact_edunomics,
    core.fact_teacher_effectiveness,
    core.fact_teacher_experience,
    core.fact_educator_credentials_wide,
    core.fact_graduation_rate_wide;

INSERT INTO core.fact_teacher_demographics (
    school_key,
    year,
    gender,
    race,
    ethnicity,
    sub_population,
    demographic_count,
    demographic_rate,
    imputed_flag,
    imputation_method,
    _created_at,
    _updated_at
)
SELECT
    m.school_key,
    s.year,
    s.gender,
    s.race,
    s.ethnicity,
    s.sub_population,
    s.demographic_count,
    s.demographic_rate,
    s.imputed_flag,
    s.imputation_method,
    coalesce(s._created_at, now()),
    now()
FROM sandbox.fact_teacher_demographics_long_review s
JOIN _school_key_map m
  ON m.year = s.year
 AND m.dist_name_norm = pg_temp.norm_name(s.dist_name)
 AND m.school_name_norm = pg_temp.norm_name(s.school_name);

INSERT INTO core.fact_student_demographics (
    school_key,
    year,
    grade,
    gender,
    ethnicity,
    race,
    sub_population,
    demographic_count,
    _created_at,
    _updated_at
)
SELECT
    m.school_key,
    s.year,
    s.grade,
    s.gender,
    s.ethnicity,
    s.race,
    coalesce(s.sub_population, 'Unknown SubPopulation'),
    s.demographic_count,
    coalesce(s._created_at, now()),
    now()
FROM sandbox.fact_student_demographics_long_review s
JOIN _school_key_map m
  ON m.year = s.year
 AND m.dist_name_norm = pg_temp.norm_name(s.dist_name)
 AND m.school_name_norm = pg_temp.norm_name(s.school_name);

INSERT INTO core.fact_accountability (
    school_key,
    year,
    indicator,
    grade,
    gender,
    race,
    ethnicity,
    sub_population,
    score,
    _created_at,
    _updated_at
)
SELECT
    m.school_key,
    s.year,
    s.indicator,
    s.grade,
    s.gender,
    s.race,
    s.ethnicity,
    s.sub_population,
    s.score,
    coalesce(s._created_at, now()),
    now()
FROM sandbox.fact_accountability_review s
JOIN _school_key_map m
  ON m.year = s.year
 AND m.dist_name_norm = pg_temp.norm_name(s.dist_name)
 AND m.school_name_norm = pg_temp.norm_name(s.school_name);

WITH edunomics_mapped AS (
    SELECT
        m.school_key,
        s.year,
        s.ncesenroll,
        s.gradespan,
        s.level,
        s.enroll_raw,
        s.state_local_per_pupil,
        s.state_local_fund,
        s.nces_fund,
        s.nces_poverty,
        s.title_i_status,
        s.nces_charter,
        s.nces_magnet,
        s.nces_freelunch,
        s.nces_reducedlunch,
        s.per_pupil_nces_raw,
        s.per_pupil_total_raw,
        s.per_pupil_total_norm_nerds,
        s.per_pupil_site_stloc_raw_al,
        s.per_pupil_site_nces_raw_al,
        s.per_pupil_site_raw_al,
        s.per_pupil_centshare_stloc_raw_al,
        s.per_pupil_centshare_nces_raw_al,
        s.per_pupil_centshare_raw_al,
        s.flag_nerds,
        s.flag_f33,
        coalesce(s._created_at, now()) AS _created_at,
        now() AS _updated_at,
        ROW_NUMBER() OVER (
            PARTITION BY
                s.school_year_label,
                pg_temp.norm_name(s.dist_name),
                pg_temp.norm_name(s.school_name)
            ORDER BY
                CASE
                    WHEN s.state_dist_id IS NOT NULL
                     AND s.state_school_id IS NOT NULL
                     AND m.state_dist_id = s.state_dist_id
                     AND m.state_school_id = s.state_school_id THEN 0
                    ELSE 1
                END,
                m.school_key
        ) AS rn
    FROM sandbox.fact_edunomics_review s
    JOIN _school_key_map m
      ON m.year = s.year
     AND (
            (
                s.state_dist_id IS NOT NULL
                AND s.state_school_id IS NOT NULL
                AND m.state_dist_id = s.state_dist_id
                AND m.state_school_id = s.state_school_id
            )
            OR (
                m.dist_name_norm = pg_temp.norm_name(s.dist_name)
                AND m.school_name_norm = pg_temp.norm_name(s.school_name)
            )
        )
)
INSERT INTO core.fact_edunomics (
    school_key,
    year,
    ncesenroll,
    gradespan,
    level,
    enroll_raw,
    state_local_per_pupil,
    state_local_fund,
    nces_fund,
    nces_poverty,
    title_i_status,
    nces_charter,
    nces_magnet,
    nces_freelunch,
    nces_reducedlunch,
    per_pupil_nces_raw,
    per_pupil_total_raw,
    per_pupil_total_norm_nerds,
    per_pupil_site_stloc_raw_al,
    per_pupil_site_nces_raw_al,
    per_pupil_site_raw_al,
    per_pupil_centshare_stloc_raw_al,
    per_pupil_centshare_nces_raw_al,
    per_pupil_centshare_raw_al,
    flag_nerds,
    flag_f33,
    _created_at,
    _updated_at
)
SELECT
    school_key,
    year,
    ncesenroll,
    gradespan,
    level,
    enroll_raw,
    state_local_per_pupil,
    state_local_fund,
    nces_fund,
    nces_poverty,
    title_i_status,
    nces_charter,
    nces_magnet,
    nces_freelunch,
    nces_reducedlunch,
    per_pupil_nces_raw,
    per_pupil_total_raw,
    per_pupil_total_norm_nerds,
    per_pupil_site_stloc_raw_al,
    per_pupil_site_nces_raw_al,
    per_pupil_site_raw_al,
    per_pupil_centshare_stloc_raw_al,
    per_pupil_centshare_nces_raw_al,
    per_pupil_centshare_raw_al,
    flag_nerds,
    flag_f33,
    _created_at,
    _updated_at
FROM edunomics_mapped
WHERE rn = 1;

INSERT INTO core.fact_teacher_effectiveness (
    school_key,
    year,
    score,
    atot_completion_rate_designation,
    title_i_status,
    _created_at,
    _updated_at
)
SELECT
    m.school_key,
    s.year,
    s.score,
    s.atot_completion_rate_designation,
    s.title_i_status,
    coalesce(s._created_at, now()),
    now()
FROM sandbox.fact_teacher_effectiveness_review s
JOIN _school_key_map m
  ON m.year = s.year
 AND m.dist_name_norm = pg_temp.norm_name(s.dist_name)
 AND m.school_name_norm = pg_temp.norm_name(s.school_name);

INSERT INTO core.fact_teacher_experience (
    school_key,
    year,
    gender,
    race,
    ethnicity,
    sub_population,
    total_count,
    exp_count,
    exp_rate,
    inexp_count,
    inexp_rate,
    _created_at,
    _updated_at
)
SELECT
    m.school_key,
    s.year,
    s.gender,
    s.race,
    s.ethnicity,
    s.sub_population,
    s.total_count,
    s.exp_count,
    s.exp_rate,
    s.inexp_count,
    s.inexp_rate,
    coalesce(s._created_at, now()),
    now()
FROM sandbox.fact_teacher_experience_review s
JOIN _school_key_map m
  ON m.year = s.year
 AND m.dist_name_norm = pg_temp.norm_name(s.dist_name)
 AND m.school_name_norm = pg_temp.norm_name(s.school_name);

INSERT INTO core.fact_educator_credentials_wide (
    school_key,
    year,
    gender,
    race,
    ethnicity,
    sub_population,
    total_count_all_degree,
    credential_count_all_degree,
    credential_rate_all_degree,
    credential_count_six_year_class_aa,
    credential_rate_six_year_class_aa,
    credential_count_masters_degree_class_a,
    credential_rate_masters_degree_class_a,
    credential_count_bachelors_degree_class_b,
    credential_rate_bachelors_degree_class_b,
    credential_count_not_specified,
    credential_rate_not_specified,
    credential_count_emergency_certificates,
    credential_rate_emergency_certificates,
    credential_count_provisional_certificates,
    credential_rate_provisional_certificates,
    _created_at,
    _updated_at
)
SELECT
    m.school_key,
    s.year,
    s.gender,
    s.race,
    s.ethnicity,
    s.sub_population,
    s.total_count_all_degree,
    s.credential_count_all_degree,
    s.credential_rate_all_degree,
    s.credential_count_six_year_class_aa,
    s.credential_rate_six_year_class_aa,
    s.credential_count_masters_degree_class_a,
    s.credential_rate_masters_degree_class_a,
    s.credential_count_bachelors_degree_class_b,
    s.credential_rate_bachelors_degree_class_b,
    s.credential_count_not_specified,
    s.credential_rate_not_specified,
    s.credential_count_emergency_certificates,
    s.credential_rate_emergency_certificates,
    s.credential_count_provisional_certificates,
    s.credential_rate_provisional_certificates,
    coalesce(s._created_at, now()),
    now()
FROM sandbox.fact_educator_credentials_wide_review s
JOIN _school_key_map m
  ON m.year = s.year
 AND m.dist_name_norm = pg_temp.norm_name(s.dist_name)
 AND m.school_name_norm = pg_temp.norm_name(s.school_name);

INSERT INTO core.fact_graduation_rate_wide (
    school_key,
    year,
    student_count,
    graduates,
    graduation_percent,
    ccr_attainment,
    ccr_attainment_percent,
    _created_at,
    _updated_at
)
SELECT
    m.school_key,
    s.year,
    s.student_count,
    s.graduates,
    s.graduation_percent,
    s.ccr_attainment,
    s.ccr_attainment_percent,
    coalesce(s._created_at, now()),
    now()
FROM sandbox.fact_graduation_rate_wide_review s
JOIN _school_key_map m
  ON m.year = s.year
 AND m.dist_name_norm = pg_temp.norm_name(s.dist_name)
 AND m.school_name_norm = pg_temp.norm_name(s.school_name);

COMMIT;

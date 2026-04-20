-- Rebuild core reviewed school + fact tables from sandbox.
-- Run after review approval.

BEGIN;

CREATE SCHEMA IF NOT EXISTS core;

DROP MATERIALIZED VIEW IF EXISTS core.mv_student_census_features;
DROP MATERIALIZED VIEW IF EXISTS core.mv_student_race_pivot;
DROP MATERIALIZED VIEW IF EXISTS core.mv_staff_census_features;
DROP MATERIALIZED VIEW IF EXISTS core.mv_teacher_race_pivot;
DROP MATERIALIZED VIEW IF EXISTS core.mv_teacher_experience_pivot;

DROP TABLE IF EXISTS core.fact_teacher_demographics;
DROP TABLE IF EXISTS core.fact_student_demographics;
DROP TABLE IF EXISTS core.fact_accountability;
DROP TABLE IF EXISTS core.fact_edunomics;
DROP TABLE IF EXISTS core.fact_teacher_effectiveness;
DROP TABLE IF EXISTS core.fact_teacher_experience;
DROP TABLE IF EXISTS core.bridge_school_geo_county;
DROP TABLE IF EXISTS core.fact_school_outcomes_wide;
DROP TABLE IF EXISTS core.bridge_school_year;
DROP TABLE IF EXISTS core.dim_school;
DROP TABLE IF EXISTS core.dim_district;
DROP TABLE IF EXISTS core.dim_state;
DROP TABLE IF EXISTS core.dim_school_info;

CREATE TABLE core.dim_state (
    state_key        BIGINT PRIMARY KEY,
    state_code       CHAR(2) NOT NULL UNIQUE,
    department_name  TEXT NOT NULL,
    _created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE core.dim_district (
    district_key           BIGINT PRIMARY KEY,
    state_key              BIGINT NOT NULL REFERENCES core.dim_state(state_key),
    state_code             CHAR(2) NOT NULL,
    district_name          TEXT NOT NULL,
    district_name_norm     TEXT NOT NULL,
    state_dist_id          INTEGER,
    nces_admin_id          BIGINT,
    source_state_dist_id   TEXT,
    _created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_core_dim_district UNIQUE (state_code, district_name_norm)
);

CREATE TABLE core.dim_school (
    school_key             BIGINT PRIMARY KEY,
    district_key           BIGINT NOT NULL REFERENCES core.dim_district(district_key),
    state_code             CHAR(2) NOT NULL,
    school_name            TEXT NOT NULL,
    school_name_norm       TEXT NOT NULL,
    state_school_id        INTEGER,
    nces_geo_id            BIGINT,
    census_id              BIGINT,
    nces_id                BIGINT,
    nces_charter           BOOLEAN,
    nces_magnet            BOOLEAN,
    nces_address           TEXT,
    nces_city              VARCHAR(120),
    nces_zip               VARCHAR(15),
    source_state_school_id TEXT,
    _created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_core_dim_school UNIQUE (district_key, school_name_norm)
);

CREATE TABLE core.bridge_school_year (
    school_key           BIGINT NOT NULL REFERENCES core.dim_school(school_key),
    school_year_label    VARCHAR(9) NOT NULL,
    school_year_start    SMALLINT NOT NULL,
    school_year_end      SMALLINT,
    nces_locale_key      SMALLINT NOT NULL REFERENCES ref.nces_locale_canonical(nces_locale_key),
    nces_locale_type     VARCHAR(20),
    nces_locale_subtype  VARCHAR(20),
    source_nces_locale   TEXT,
    _source_file         TEXT,
    _ingested_at         TIMESTAMP,
    _created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_core_bridge_school_year PRIMARY KEY (school_key, school_year_start)
);

CREATE TABLE core.dim_school_info (
    school_key             BIGINT NOT NULL,
    school_year_label      VARCHAR(9) NOT NULL,
    school_year_start      SMALLINT NOT NULL,
    school_year_end        SMALLINT,
    state_code             CHAR(2) NOT NULL,
    state_dist_id          INTEGER,
    state_school_id        INTEGER,
    nces_admin_id          BIGINT,
    nces_geo_id            BIGINT,
    census_id              BIGINT,
    nces_id                BIGINT,
    dist_name              TEXT NOT NULL,
    school_name            TEXT NOT NULL,
    nces_locale_key        SMALLINT NOT NULL REFERENCES ref.nces_locale_canonical(nces_locale_key),
    nces_locale_type       VARCHAR(20),
    nces_locale_subtype    VARCHAR(20),
    source_nces_locale     TEXT,
    nces_charter           BOOLEAN,
    nces_magnet            BOOLEAN,
    nces_address           TEXT,
    nces_city              VARCHAR(120),
    nces_zip               VARCHAR(15),
    _created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_core_dim_school_info PRIMARY KEY (school_key, school_year_start),
    CONSTRAINT uq_core_school_bk UNIQUE (school_year_label, dist_name, school_name)
);

CREATE TABLE core.fact_teacher_demographics (
    school_key         BIGINT NOT NULL,
    year               SMALLINT NOT NULL,
    gender             TEXT NOT NULL REFERENCES ref.gender_canonical(canonical_value),
    race               TEXT NOT NULL REFERENCES ref.race_canonical(canonical_value),
    ethnicity          TEXT NOT NULL REFERENCES ref.ethnicity_canonical(canonical_value),
    sub_population     TEXT NOT NULL REFERENCES ref.staff_position_canonical(canonical_value),
    demographic_count  DOUBLE PRECISION,
    demographic_rate   DOUBLE PRECISION,
    imputed_flag       BOOLEAN NOT NULL DEFAULT FALSE,
    imputation_method  TEXT,
    _created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_core_teacher_long PRIMARY KEY
      (school_key, year, gender, race, ethnicity, sub_population),
    CONSTRAINT fk_core_teacher_demo_school_year FOREIGN KEY (school_key, year)
      REFERENCES core.dim_school_info(school_key, school_year_start)
);

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
    coalesce(s._updated_at::timestamptz, now())
FROM sandbox.dim_state_review s;

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
    coalesce(d._updated_at::timestamptz, now())
FROM sandbox.dim_district_review d;

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
    coalesce(s._updated_at::timestamptz, now())
FROM sandbox.dim_school_review s;

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
    coalesce(b._updated_at::timestamptz, now())
FROM sandbox.bridge_school_year_review b;

CREATE TABLE core.fact_student_demographics (
    school_key         BIGINT NOT NULL,
    year               SMALLINT NOT NULL,
    grade              VARCHAR(30),
    gender             TEXT NOT NULL REFERENCES ref.gender_canonical(canonical_value),
    ethnicity          TEXT NOT NULL REFERENCES ref.ethnicity_canonical(canonical_value),
    race               TEXT NOT NULL REFERENCES ref.race_canonical(canonical_value),
    sub_population     TEXT,
    demographic_count  NUMERIC(14,2),
    _created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_core_student_long PRIMARY KEY
      (school_key, year, grade, gender, ethnicity, race, sub_population),
    CONSTRAINT fk_core_student_demo_school_year FOREIGN KEY (school_key, year)
      REFERENCES core.dim_school_info(school_key, school_year_start)
);

CREATE TABLE core.fact_accountability (
    school_key        BIGINT NOT NULL,
    year              SMALLINT NOT NULL,
    indicator         TEXT NOT NULL,
    grade             VARCHAR(30) NOT NULL,
    gender            TEXT NOT NULL REFERENCES ref.gender_canonical(canonical_value),
    race              TEXT NOT NULL REFERENCES ref.race_canonical(canonical_value),
    ethnicity         TEXT NOT NULL REFERENCES ref.ethnicity_canonical(canonical_value),
    sub_population    TEXT NOT NULL,
    score             TEXT,
    _created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_core_fact_accountability
      UNIQUE NULLS NOT DISTINCT
      (school_key, year, indicator, grade, gender, race, ethnicity, sub_population),
    CONSTRAINT fk_core_accountability_school_year FOREIGN KEY (school_key, year)
      REFERENCES core.dim_school_info(school_key, school_year_start)
);

CREATE TABLE core.fact_edunomics (
    school_key                        BIGINT NOT NULL,
    year                              SMALLINT NOT NULL,
    ncesenroll                        INTEGER,
    gradespan                         VARCHAR(30),
    level                             SMALLINT,
    enroll_raw                        INTEGER,
    state_local_per_pupil             NUMERIC(14,2),
    state_local_fund                  NUMERIC(16,2),
    nces_fund                         NUMERIC(16,2),
    nces_poverty                      NUMERIC(8,4),
    title_i_status                    VARCHAR(30) NOT NULL,
    nces_charter                      BOOLEAN,
    nces_magnet                       BOOLEAN,
    nces_freelunch                    INTEGER,
    nces_reducedlunch                 INTEGER,
    per_pupil_nces_raw                NUMERIC(14,2),
    per_pupil_total_raw               NUMERIC(14,2),
    per_pupil_total_norm_nerds        NUMERIC(14,2),
    per_pupil_site_stloc_raw_al       INTEGER,
    per_pupil_site_nces_raw_al        INTEGER,
    per_pupil_site_raw_al             INTEGER,
    per_pupil_centshare_stloc_raw_al  INTEGER,
    per_pupil_centshare_nces_raw_al   INTEGER,
    per_pupil_centshare_raw_al        INTEGER,
    flag_nerds                        BOOLEAN,
    flag_f33                          BOOLEAN,
    _created_at                       TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at                       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_core_fact_edunomics PRIMARY KEY (school_key, year),
    CONSTRAINT ck_core_fact_edunomics_title_i_status
      CHECK (title_i_status IN ('UNREPORTED', 'NON_TITLE_I', 'TARGETED_ASSISTANCE', 'SCHOOLWIDE')),
    CONSTRAINT fk_core_edunomics_school_year FOREIGN KEY (school_key, year)
      REFERENCES core.dim_school_info(school_key, school_year_start)
);

CREATE TABLE core.fact_teacher_effectiveness (
    school_key                        BIGINT NOT NULL,
    year                              SMALLINT NOT NULL,
    score                             TEXT,
    atot_completion_rate_designation  TEXT,
    title_i_status                    VARCHAR(30),
    _created_at                       TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at                       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_core_fact_teacher_effectiveness PRIMARY KEY (school_key, year),
    CONSTRAINT fk_core_teacher_effect_school_year FOREIGN KEY (school_key, year)
      REFERENCES core.dim_school_info(school_key, school_year_start)
);

CREATE TABLE core.fact_teacher_experience (
    school_key        BIGINT NOT NULL,
    year              SMALLINT NOT NULL,
    gender            TEXT NOT NULL REFERENCES ref.gender_canonical(canonical_value),
    race              TEXT NOT NULL REFERENCES ref.race_canonical(canonical_value),
    ethnicity         TEXT NOT NULL REFERENCES ref.ethnicity_canonical(canonical_value),
    sub_population    TEXT NOT NULL,
    total_count       NUMERIC(14,2),
    exp_count         NUMERIC(14,2),
    exp_rate          NUMERIC(8,4),
    inexp_count       NUMERIC(14,2),
    inexp_rate        NUMERIC(8,4),
    _created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_core_fact_teacher_experience
      UNIQUE NULLS NOT DISTINCT (school_key, year, gender, race, ethnicity, sub_population),
    CONSTRAINT fk_core_teacher_exp_school_year FOREIGN KEY (school_key, year)
      REFERENCES core.dim_school_info(school_key, school_year_start)
);

INSERT INTO core.dim_school_info (
    school_key, school_year_label, school_year_start, school_year_end,
    state_code, state_dist_id, state_school_id,
    nces_admin_id, nces_geo_id, census_id, nces_id,
    dist_name, school_name,
    nces_locale_key, nces_locale_type, nces_locale_subtype, source_nces_locale,
    nces_charter, nces_magnet, nces_address, nces_city, nces_zip,
    _created_at, _updated_at
)
SELECT
    sy.school_key,
    sy.school_year_label,
    sy.school_year_start,
    sy.school_year_end,
    s.state_code,
    d.state_dist_id,
    s.state_school_id,
    d.nces_admin_id,
    s.nces_geo_id,
    s.census_id,
    s.nces_id,
    d.district_name,
    s.school_name,
    sy.nces_locale_key,
    sy.nces_locale_type,
    sy.nces_locale_subtype,
    sy.source_nces_locale,
    s.nces_charter,
    s.nces_magnet,
    s.nces_address,
    s.nces_city,
    s.nces_zip,
    now(),
    now()
FROM core.bridge_school_year sy
JOIN core.dim_school s ON s.school_key = sy.school_key
JOIN core.dim_district d ON d.district_key = s.district_key;

INSERT INTO core.fact_teacher_demographics (
    school_key, year, gender, race, ethnicity, sub_population,
    demographic_count, demographic_rate, imputed_flag, imputation_method,
    _created_at, _updated_at
)
SELECT
    d.school_key,
    s.year,
    s.gender,
    s.race,
    s.ethnicity,
    s.sub_population,
    s.demographic_count,
    s.demographic_rate,
    s.imputed_flag,
    s.imputation_method,
    s._created_at,
    s._updated_at
FROM sandbox.fact_teacher_demographics_long_review s
JOIN core.dim_school_info d
  ON d.school_year_start = s.year
 AND lower(trim(regexp_replace(d.dist_name, '[[:space:]]+', ' ', 'g'))) = lower(trim(regexp_replace(s.dist_name, '[[:space:]]+', ' ', 'g')))
 AND lower(trim(regexp_replace(d.school_name, '[[:space:]]+', ' ', 'g'))) = lower(trim(regexp_replace(s.school_name, '[[:space:]]+', ' ', 'g')))
ON CONFLICT (school_key, year, gender, race, ethnicity, sub_population) DO UPDATE SET
    demographic_count = EXCLUDED.demographic_count,
    demographic_rate  = EXCLUDED.demographic_rate,
    imputed_flag      = EXCLUDED.imputed_flag,
    imputation_method = EXCLUDED.imputation_method,
    _updated_at       = now();

INSERT INTO core.fact_student_demographics (
    school_key, year, grade, gender, ethnicity, race, sub_population,
    demographic_count, _created_at, _updated_at
)
SELECT
    d.school_key,
    s.year,
    s.grade,
    s.gender,
    s.ethnicity,
    s.race,
    s.sub_population,
    s.demographic_count,
    s._created_at,
    s._updated_at
FROM sandbox.fact_student_demographics_long_review s
JOIN core.dim_school_info d
  ON d.school_year_start = s.year
 AND lower(trim(regexp_replace(d.dist_name, '[[:space:]]+', ' ', 'g'))) = lower(trim(regexp_replace(s.dist_name, '[[:space:]]+', ' ', 'g')))
 AND lower(trim(regexp_replace(d.school_name, '[[:space:]]+', ' ', 'g'))) = lower(trim(regexp_replace(s.school_name, '[[:space:]]+', ' ', 'g')))
ON CONFLICT (school_key, year, grade, gender, ethnicity, race, sub_population) DO UPDATE SET
    demographic_count = EXCLUDED.demographic_count,
    _updated_at       = now();

INSERT INTO core.fact_accountability (
    school_key, year, indicator, grade, gender, race, ethnicity, sub_population,
    score, _created_at, _updated_at
)
SELECT
    d.school_key,
    s.year,
    s.indicator,
    s.grade,
    s.gender,
    s.race,
    s.ethnicity,
    s.sub_population,
    s.score,
    s._created_at,
    s._updated_at
FROM sandbox.fact_accountability_review s
JOIN core.dim_school_info d
  ON d.school_year_start = s.year
 AND lower(trim(regexp_replace(d.dist_name, '[[:space:]]+', ' ', 'g'))) = lower(trim(regexp_replace(s.dist_name, '[[:space:]]+', ' ', 'g')))
 AND lower(trim(regexp_replace(d.school_name, '[[:space:]]+', ' ', 'g'))) = lower(trim(regexp_replace(s.school_name, '[[:space:]]+', ' ', 'g')))
ON CONFLICT (school_key, year, indicator, grade, gender, race, ethnicity, sub_population) DO UPDATE SET
    score       = EXCLUDED.score,
    _updated_at = now();

INSERT INTO core.fact_edunomics (
    school_key, year, ncesenroll, gradespan, level, enroll_raw,
    state_local_per_pupil, state_local_fund, nces_fund, nces_poverty,
    title_i_status, nces_charter, nces_magnet,
    nces_freelunch, nces_reducedlunch,
    per_pupil_nces_raw, per_pupil_total_raw, per_pupil_total_norm_nerds,
    per_pupil_site_stloc_raw_al, per_pupil_site_nces_raw_al, per_pupil_site_raw_al,
    per_pupil_centshare_stloc_raw_al, per_pupil_centshare_nces_raw_al, per_pupil_centshare_raw_al,
    flag_nerds, flag_f33, _created_at, _updated_at
)
WITH edunomics_mapped AS (
    SELECT
        d.school_key,
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
        s._created_at,
        s._updated_at,
        ROW_NUMBER() OVER (
            PARTITION BY s.school_year_label, s.dist_name, s.school_name
            ORDER BY
                CASE
                    WHEN s.state_dist_id IS NOT NULL
                     AND s.state_school_id IS NOT NULL
                     AND d.state_dist_id = s.state_dist_id
                     AND d.state_school_id = s.state_school_id THEN 0
                    ELSE 1
                END,
                d.school_key
        ) AS rn
    FROM sandbox.fact_edunomics_review s
    JOIN core.dim_school_info d
      ON d.school_year_label = s.school_year_label
     AND (
        (
            s.state_dist_id IS NOT NULL
            AND s.state_school_id IS NOT NULL
            AND d.state_dist_id = s.state_dist_id
            AND d.state_school_id = s.state_school_id
        )
        OR (
            lower(trim(regexp_replace(d.dist_name, '[[:space:]]+', ' ', 'g'))) = lower(trim(regexp_replace(s.dist_name, '[[:space:]]+', ' ', 'g')))
            AND lower(trim(regexp_replace(d.school_name, '[[:space:]]+', ' ', 'g'))) = lower(trim(regexp_replace(s.school_name, '[[:space:]]+', ' ', 'g')))
        )
     )
)
SELECT
    school_key, year, ncesenroll, gradespan, level, enroll_raw,
    state_local_per_pupil, state_local_fund, nces_fund, nces_poverty,
    title_i_status, nces_charter, nces_magnet,
    nces_freelunch, nces_reducedlunch,
    per_pupil_nces_raw, per_pupil_total_raw, per_pupil_total_norm_nerds,
    per_pupil_site_stloc_raw_al, per_pupil_site_nces_raw_al, per_pupil_site_raw_al,
    per_pupil_centshare_stloc_raw_al, per_pupil_centshare_nces_raw_al, per_pupil_centshare_raw_al,
    flag_nerds, flag_f33, _created_at, _updated_at
FROM edunomics_mapped
WHERE rn = 1
ON CONFLICT (school_key, year) DO UPDATE SET
    ncesenroll                       = EXCLUDED.ncesenroll,
    gradespan                        = EXCLUDED.gradespan,
    level                            = EXCLUDED.level,
    enroll_raw                       = EXCLUDED.enroll_raw,
    state_local_per_pupil            = EXCLUDED.state_local_per_pupil,
    state_local_fund                 = EXCLUDED.state_local_fund,
    nces_fund                        = EXCLUDED.nces_fund,
    nces_poverty                     = EXCLUDED.nces_poverty,
    title_i_status                   = EXCLUDED.title_i_status,
    nces_charter                     = EXCLUDED.nces_charter,
    nces_magnet                      = EXCLUDED.nces_magnet,
    nces_freelunch                   = EXCLUDED.nces_freelunch,
    nces_reducedlunch                = EXCLUDED.nces_reducedlunch,
    per_pupil_nces_raw               = EXCLUDED.per_pupil_nces_raw,
    per_pupil_total_raw              = EXCLUDED.per_pupil_total_raw,
    per_pupil_total_norm_nerds       = EXCLUDED.per_pupil_total_norm_nerds,
    per_pupil_site_stloc_raw_al      = EXCLUDED.per_pupil_site_stloc_raw_al,
    per_pupil_site_nces_raw_al       = EXCLUDED.per_pupil_site_nces_raw_al,
    per_pupil_site_raw_al            = EXCLUDED.per_pupil_site_raw_al,
    per_pupil_centshare_stloc_raw_al = EXCLUDED.per_pupil_centshare_stloc_raw_al,
    per_pupil_centshare_nces_raw_al  = EXCLUDED.per_pupil_centshare_nces_raw_al,
    per_pupil_centshare_raw_al       = EXCLUDED.per_pupil_centshare_raw_al,
    flag_nerds                       = EXCLUDED.flag_nerds,
    flag_f33                         = EXCLUDED.flag_f33,
    _updated_at                      = now();

INSERT INTO core.fact_teacher_effectiveness (
    school_key, year, score, atot_completion_rate_designation, title_i_status,
    _created_at, _updated_at
)
SELECT
    d.school_key,
    s.year,
    s.score,
    s.atot_completion_rate_designation,
    s.title_i_status,
    s._created_at,
    s._updated_at
FROM sandbox.fact_teacher_effectiveness_review s
JOIN core.dim_school_info d
  ON d.school_year_start = s.year
 AND lower(trim(regexp_replace(d.dist_name, '[[:space:]]+', ' ', 'g'))) = lower(trim(regexp_replace(s.dist_name, '[[:space:]]+', ' ', 'g')))
 AND lower(trim(regexp_replace(d.school_name, '[[:space:]]+', ' ', 'g'))) = lower(trim(regexp_replace(s.school_name, '[[:space:]]+', ' ', 'g')))
ON CONFLICT (school_key, year) DO UPDATE SET
    score                            = EXCLUDED.score,
    atot_completion_rate_designation = EXCLUDED.atot_completion_rate_designation,
    title_i_status                   = EXCLUDED.title_i_status,
    _updated_at                      = now();

INSERT INTO core.fact_teacher_experience (
    school_key, year, gender, race, ethnicity, sub_population,
    total_count, exp_count, exp_rate, inexp_count, inexp_rate,
    _created_at, _updated_at
)
SELECT
    d.school_key,
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
    s._created_at,
    s._updated_at
FROM sandbox.fact_teacher_experience_review s
JOIN core.dim_school_info d
  ON d.school_year_start = s.year
 AND lower(trim(regexp_replace(d.dist_name, '[[:space:]]+', ' ', 'g'))) = lower(trim(regexp_replace(s.dist_name, '[[:space:]]+', ' ', 'g')))
 AND lower(trim(regexp_replace(d.school_name, '[[:space:]]+', ' ', 'g'))) = lower(trim(regexp_replace(s.school_name, '[[:space:]]+', ' ', 'g')))
ON CONFLICT (school_key, year, gender, race, ethnicity, sub_population) DO UPDATE SET
    total_count = EXCLUDED.total_count,
    exp_count   = EXCLUDED.exp_count,
    exp_rate    = EXCLUDED.exp_rate,
    inexp_count = EXCLUDED.inexp_count,
    inexp_rate  = EXCLUDED.inexp_rate,
    _updated_at = now();

COMMIT;

-- Upsert reviewed sandbox tables into core.
-- Run after review approval.

BEGIN;

CREATE SCHEMA IF NOT EXISTS core;

CREATE TABLE IF NOT EXISTS core.dim_school_info (
    school_key             BIGINT PRIMARY KEY,
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
    CONSTRAINT uq_core_school_bk UNIQUE (school_year_label, dist_name, school_name)
);

CREATE TABLE IF NOT EXISTS core.fact_teacher_demographics (
    school_key         BIGINT NOT NULL REFERENCES core.dim_school_info(school_key),
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
      (school_key, year, gender, race, ethnicity, sub_population)
);

CREATE TABLE IF NOT EXISTS core.fact_student_demographics (
    school_key         BIGINT NOT NULL REFERENCES core.dim_school_info(school_key),
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
      (school_key, year, grade, gender, ethnicity, race, sub_population)
);

ALTER TABLE core.fact_student_demographics
DROP COLUMN IF EXISTS graduation_year;

CREATE TABLE IF NOT EXISTS core.fact_accountability (
    school_key        BIGINT NOT NULL REFERENCES core.dim_school_info(school_key),
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
      (school_key, year, indicator, grade, gender, race, ethnicity, sub_population)
);

CREATE TABLE IF NOT EXISTS core.fact_edunomics (
    school_key                        BIGINT NOT NULL REFERENCES core.dim_school_info(school_key),
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
      CHECK (title_i_status IN ('UNREPORTED', 'NON_TITLE_I', 'TARGETED_ASSISTANCE', 'SCHOOLWIDE'))
);

ALTER TABLE core.fact_edunomics
DROP COLUMN IF EXISTS nces_title1;

ALTER TABLE core.fact_edunomics
DROP COLUMN IF EXISTS nces_title1_schoolwide;

CREATE TABLE IF NOT EXISTS core.fact_teacher_effectiveness (
    school_key                        BIGINT NOT NULL REFERENCES core.dim_school_info(school_key),
    year                              SMALLINT NOT NULL,
    score                             TEXT,
    atot_completion_rate_designation  TEXT,
    title_i_status                    VARCHAR(30),
    _created_at                       TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at                       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_core_fact_teacher_effectiveness PRIMARY KEY (school_key, year)
);

CREATE TABLE IF NOT EXISTS core.fact_teacher_experience (
    school_key        BIGINT NOT NULL REFERENCES core.dim_school_info(school_key),
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
      UNIQUE NULLS NOT DISTINCT (school_key, year, gender, race, ethnicity, sub_population)
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
    school_key, school_year_label, school_year_start, school_year_end,
    state_code, state_dist_id, state_school_id,
    nces_admin_id, nces_geo_id, census_id, nces_id,
    dist_name, school_name,
    nces_locale_key, nces_locale_type, nces_locale_subtype, source_nces_locale,
    nces_charter, nces_magnet, nces_address, nces_city, nces_zip,
    _created_at, _updated_at
FROM sandbox.dim_school_info_review_v2
ON CONFLICT (school_key) DO UPDATE SET
    school_year_label   = EXCLUDED.school_year_label,
    school_year_start   = EXCLUDED.school_year_start,
    school_year_end     = EXCLUDED.school_year_end,
    state_code          = EXCLUDED.state_code,
    state_dist_id       = EXCLUDED.state_dist_id,
    state_school_id     = EXCLUDED.state_school_id,
    nces_admin_id       = EXCLUDED.nces_admin_id,
    nces_geo_id         = EXCLUDED.nces_geo_id,
    census_id           = EXCLUDED.census_id,
    nces_id             = EXCLUDED.nces_id,
    dist_name           = EXCLUDED.dist_name,
    school_name         = EXCLUDED.school_name,
    nces_locale_key     = EXCLUDED.nces_locale_key,
    nces_locale_type    = EXCLUDED.nces_locale_type,
    nces_locale_subtype = EXCLUDED.nces_locale_subtype,
    source_nces_locale  = EXCLUDED.source_nces_locale,
    nces_charter        = EXCLUDED.nces_charter,
    nces_magnet         = EXCLUDED.nces_magnet,
    nces_address        = EXCLUDED.nces_address,
    nces_city           = EXCLUDED.nces_city,
    nces_zip            = EXCLUDED.nces_zip,
    _updated_at         = now();

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

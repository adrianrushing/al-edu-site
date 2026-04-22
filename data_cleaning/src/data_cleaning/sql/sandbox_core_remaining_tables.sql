-- Build and populate remaining core-aligned review fact tables in sandbox.

DROP TABLE IF EXISTS sandbox.fact_teacher_experience_review;
DROP TABLE IF EXISTS sandbox.fact_teacher_effectiveness_review;
DROP TABLE IF EXISTS sandbox.fact_edunomics_review;
DROP TABLE IF EXISTS sandbox.fact_accountability_review;
DROP TABLE IF EXISTS sandbox.fact_graduation_rate_wide_review;
DROP TABLE IF EXISTS sandbox.fact_graduation_rate_review;
DROP TABLE IF EXISTS sandbox.fact_educator_credentials_wide_review;
DROP TABLE IF EXISTS sandbox.fact_educator_credentials_review;

CREATE TABLE sandbox.fact_accountability_review (
    year              SMALLINT NOT NULL,
    dist_name         TEXT NOT NULL,
    school_name       TEXT NOT NULL,
    indicator         TEXT NOT NULL,
    grade             VARCHAR(30) NOT NULL,
    gender            TEXT NOT NULL,
    race              TEXT NOT NULL,
    ethnicity         TEXT NOT NULL,
    sub_population    TEXT NOT NULL,
    score             TEXT,
    _created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_fact_accountability_review
      UNIQUE NULLS NOT DISTINCT
      (year, dist_name, school_name, indicator, grade, gender, race, ethnicity, sub_population)
);

CREATE TABLE sandbox.fact_edunomics_review (
    school_year_label                 VARCHAR(9) NOT NULL,
    year                              SMALLINT NOT NULL,
    dist_name                         TEXT NOT NULL,
    school_name                       TEXT NOT NULL,
    state_dist_id                     INTEGER,
    state_school_id                   INTEGER,
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
    CONSTRAINT uq_fact_edunomics_review
      UNIQUE NULLS NOT DISTINCT (school_year_label, dist_name, school_name),
    CONSTRAINT ck_fact_edunomics_title_i_status
      CHECK (title_i_status IN ('UNREPORTED', 'NON_TITLE_I', 'TARGETED_ASSISTANCE', 'SCHOOLWIDE'))
);

CREATE TABLE sandbox.fact_teacher_effectiveness_review (
    year                              SMALLINT NOT NULL,
    dist_name                         TEXT NOT NULL,
    school_name                       TEXT NOT NULL,
    score                             TEXT,
    atot_completion_rate_designation  TEXT,
    title_i_status                    VARCHAR(30),
    _created_at                       TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at                       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_fact_teacher_effectiveness_review
      UNIQUE NULLS NOT DISTINCT (year, dist_name, school_name)
);

CREATE TABLE sandbox.fact_teacher_experience_review (
    year              SMALLINT NOT NULL,
    dist_name         TEXT NOT NULL,
    school_name       TEXT NOT NULL,
    gender            TEXT NOT NULL,
    race              TEXT NOT NULL,
    ethnicity         TEXT NOT NULL,
    sub_population    TEXT NOT NULL,
    total_count       NUMERIC(14,2),
    exp_count         NUMERIC(14,2),
    exp_rate          NUMERIC(8,4),
    inexp_count       NUMERIC(14,2),
    inexp_rate        NUMERIC(8,4),
    _created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_fact_teacher_experience_review
      UNIQUE NULLS NOT DISTINCT
      (year, dist_name, school_name, gender, race, ethnicity, sub_population)
);

CREATE TABLE sandbox.fact_educator_credentials_review (
    year              SMALLINT NOT NULL,
    dist_name         TEXT NOT NULL,
    school_name       TEXT NOT NULL,
    gender            TEXT NOT NULL,
    race              TEXT NOT NULL,
    ethnicity         TEXT NOT NULL,
    sub_population    TEXT NOT NULL,
    degree_type       TEXT NOT NULL,
    credential_count  NUMERIC(14,2),
    total_count       NUMERIC(14,2),
    credential_rate   NUMERIC(8,4),
    _created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_fact_educator_credentials_review
      UNIQUE NULLS NOT DISTINCT
      (year, dist_name, school_name, gender, race, ethnicity, sub_population, degree_type)
);

CREATE TABLE sandbox.fact_educator_credentials_wide_review (
    year                                             SMALLINT NOT NULL,
    dist_name                                        TEXT NOT NULL,
    school_name                                      TEXT NOT NULL,
    gender                                           TEXT NOT NULL,
    race                                             TEXT NOT NULL,
    ethnicity                                        TEXT NOT NULL,
    sub_population                                   TEXT NOT NULL,
    total_count_all_degree                          NUMERIC(14,2),
    credential_count_all_degree                     NUMERIC(14,2),
    credential_rate_all_degree                      NUMERIC(8,4),
    credential_count_six_year_class_aa              NUMERIC(14,2),
    credential_rate_six_year_class_aa               NUMERIC(8,4),
    credential_count_masters_degree_class_a         NUMERIC(14,2),
    credential_rate_masters_degree_class_a          NUMERIC(8,4),
    credential_count_bachelors_degree_class_b       NUMERIC(14,2),
    credential_rate_bachelors_degree_class_b        NUMERIC(8,4),
    credential_count_not_specified                  NUMERIC(14,2),
    credential_rate_not_specified                   NUMERIC(8,4),
    credential_count_emergency_certificates         NUMERIC(14,2),
    credential_rate_emergency_certificates          NUMERIC(8,4),
    credential_count_provisional_certificates       NUMERIC(14,2),
    credential_rate_provisional_certificates        NUMERIC(8,4),
    _created_at                                     TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at                                     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_fact_educator_credentials_wide_review
      UNIQUE NULLS NOT DISTINCT
      (year, dist_name, school_name, gender, race, ethnicity, sub_population)
);

CREATE TABLE sandbox.fact_graduation_rate_review (
    year                    SMALLINT NOT NULL,
    dist_name               TEXT NOT NULL,
    school_name             TEXT NOT NULL,
    grade                   TEXT NOT NULL,
    gender                  TEXT NOT NULL,
    race                    TEXT NOT NULL,
    ethnicity               TEXT NOT NULL,
    sub_population          TEXT NOT NULL,
    student_count           NUMERIC(14,2),
    graduates               NUMERIC(14,2),
    graduation_percent      NUMERIC(8,4),
    ccr_attainment          NUMERIC(14,2),
    ccr_attainment_percent  NUMERIC(8,4),
    _created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_fact_graduation_rate_review
      UNIQUE NULLS NOT DISTINCT
      (year, dist_name, school_name, grade, gender, race, ethnicity, sub_population)
);

CREATE TABLE sandbox.fact_graduation_rate_wide_review (
    year                    SMALLINT NOT NULL,
    dist_name               TEXT NOT NULL,
    school_name             TEXT NOT NULL,
    student_count           NUMERIC(14,2),
    graduates               NUMERIC(14,2),
    graduation_percent      NUMERIC(8,4),
    ccr_attainment          NUMERIC(14,2),
    ccr_attainment_percent  NUMERIC(8,4),
    _created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_fact_graduation_rate_wide_review
      UNIQUE NULLS NOT DISTINCT (year, dist_name, school_name)
);

WITH src AS (
    SELECT
        a.year::smallint AS year,
        trim(regexp_replace(a.system, '[[:space:]]+', ' ', 'g')) AS dist_name,
        trim(regexp_replace(a.school, '[[:space:]]+', ' ', 'g')) AS school_name,
        COALESCE(NULLIF(trim(a.indicator), ''), 'Unknown Indicator') AS indicator,
        COALESCE(NULLIF(trim(a.grade), ''), 'Unknown Grade') AS grade,
        g.canonical_value AS gender,
        r.canonical_value AS race,
        e.canonical_value AS ethnicity,
        COALESCE(NULLIF(trim(a.sub_population), ''), 'Unknown SubPopulation') AS sub_population,
        NULLIF(trim(a.score), '') AS score,
        a._source_file,
        a._ingested_at,
        ROW_NUMBER() OVER (
            PARTITION BY
                a.year::smallint,
                lower(trim(regexp_replace(a.system, '[[:space:]]+', ' ', 'g'))),
                lower(trim(regexp_replace(a.school, '[[:space:]]+', ' ', 'g'))),
                COALESCE(NULLIF(trim(a.indicator), ''), 'Unknown Indicator'),
                COALESCE(NULLIF(trim(a.grade), ''), 'Unknown Grade'),
                g.canonical_value,
                r.canonical_value,
                e.canonical_value,
                COALESCE(NULLIF(trim(a.sub_population), ''), 'Unknown SubPopulation')
            ORDER BY a._ingested_at DESC NULLS LAST, a._source_file DESC NULLS LAST
        ) AS rn
    FROM staging.stg_school_accountability a
    JOIN ref.gender_canonical g
      ON g.normalized_value = lower(trim(regexp_replace(a.gender, '[[:space:]]+', ' ', 'g')))
    JOIN ref.race_canonical r
      ON r.normalized_value = lower(trim(regexp_replace(a.race, '[[:space:]]+', ' ', 'g')))
    JOIN ref.ethnicity_canonical e
      ON e.normalized_value = lower(trim(regexp_replace(a.ethnicity, '[[:space:]]+', ' ', 'g')))
    WHERE trim(COALESCE(a.year, '')) ~ '^[0-9]{4}$'
)
INSERT INTO sandbox.fact_accountability_review (
    year, dist_name, school_name, indicator, grade, gender, race, ethnicity,
    sub_population, score
)
SELECT
    year, dist_name, school_name, indicator, grade, gender, race, ethnicity,
    sub_population, score
FROM src
WHERE rn = 1;

WITH src AS (
    SELECT
        e.year AS school_year_label,
        split_part(e.year, '-', 1)::smallint AS year,
        trim(regexp_replace(e.distname, '[[:space:]]+', ' ', 'g')) AS dist_name,
        trim(regexp_replace(e.schoolname, '[[:space:]]+', ' ', 'g')) AS school_name,
        NULLIF(regexp_replace(COALESCE(e.distid_stateassigned, ''), '[^0-9]', '', 'g'), '')::INTEGER AS state_dist_id,
        NULLIF(regexp_replace(COALESCE(e.schoolid_stateassigned, ''), '[^0-9]', '', 'g'), '')::INTEGER AS state_school_id,
        CASE
            WHEN upper(trim(COALESCE(e.ncesenroll, ''))) IN ('', 'NA', 'NRD') THEN NULL
            WHEN regexp_replace(trim(e.ncesenroll), '[,$ ]', '', 'g') ~ '^[-]?[0-9]+(\.[0-9]+)?$'
                THEN regexp_replace(trim(e.ncesenroll), '[,$ ]', '', 'g')::numeric(14,2)::integer
            ELSE NULL
        END AS ncesenroll,
        NULLIF(trim(e.gradespan), '')::varchar(30) AS gradespan,
        CASE
            WHEN upper(trim(COALESCE(e.level, ''))) IN ('', 'NA', 'NRD') THEN NULL
            WHEN regexp_replace(trim(e.level), '[,$ ]', '', 'g') ~ '^[-]?[0-9]+(\.[0-9]+)?$'
                THEN regexp_replace(trim(e.level), '[,$ ]', '', 'g')::numeric(8,0)::smallint
            ELSE NULL
        END AS level,
        CASE
            WHEN upper(trim(COALESCE(e.enroll_raw_al, ''))) IN ('', 'NA', 'NRD') THEN NULL
            WHEN regexp_replace(trim(e.enroll_raw_al), '[,$ ]', '', 'g') ~ '^[-]?[0-9]+(\.[0-9]+)?$'
                THEN regexp_replace(trim(e.enroll_raw_al), '[,$ ]', '', 'g')::numeric(14,2)::integer
            ELSE NULL
        END AS enroll_raw,
        CASE
            WHEN upper(trim(COALESCE(e.pp_stloc_raw_al, ''))) IN ('', 'NA', 'NRD') THEN NULL
            WHEN regexp_replace(trim(e.pp_stloc_raw_al), '[,$ ]', '', 'g') ~ '^[-]?[0-9]+(\.[0-9]+)?$'
                THEN regexp_replace(trim(e.pp_stloc_raw_al), '[,$ ]', '', 'g')::numeric(14,2)
            ELSE NULL
        END AS state_local_per_pupil,
        CASE
            WHEN upper(trim(COALESCE(e.schoolstloc_raw_al, ''))) IN ('', 'NA', 'NRD') THEN NULL
            WHEN regexp_replace(trim(e.schoolstloc_raw_al), '[,$ ]', '', 'g') ~ '^[-]?[0-9]+(\.[0-9]+)?$'
                THEN regexp_replace(trim(e.schoolstloc_raw_al), '[,$ ]', '', 'g')::numeric(16,2)
            ELSE NULL
        END AS state_local_fund,
        CASE
            WHEN upper(trim(COALESCE(e.schoolfed_raw_al, ''))) IN ('', 'NA', 'NRD') THEN NULL
            WHEN regexp_replace(trim(e.schoolfed_raw_al), '[,$ ]', '', 'g') ~ '^[-]?[0-9]+(\.[0-9]+)?$'
                THEN regexp_replace(trim(e.schoolfed_raw_al), '[,$ ]', '', 'g')::numeric(16,2)
            ELSE NULL
        END AS nces_fund,
        CASE
            WHEN upper(trim(COALESCE(e.nces_poverty, ''))) IN ('', 'NA', 'NRD') THEN NULL
            WHEN regexp_replace(trim(e.nces_poverty), '[,$ %]', '', 'g') ~ '^[-]?[0-9]+(\.[0-9]+)?$'
                THEN regexp_replace(trim(e.nces_poverty), '[,$ %]', '', 'g')::numeric(8,4)
            ELSE NULL
        END AS nces_poverty,
        CASE
            WHEN lower(trim(COALESCE(e.nces_title1, ''))) LIKE '%not a title i%' THEN 'NON_TITLE_I'
            WHEN lower(trim(COALESCE(e.nces_title1, ''))) LIKE '%targeted assistance%' AND lower(trim(COALESCE(e.nces_title1, ''))) LIKE '%schoolwide%'
                THEN 'SCHOOLWIDE'
            WHEN lower(trim(COALESCE(e.nces_title1, ''))) LIKE '%targeted assistance%' THEN 'TARGETED_ASSISTANCE'
            WHEN lower(trim(COALESCE(e.nces_title1, ''))) IN ('yes', '1-yes')
                THEN CASE
                    WHEN lower(trim(COALESCE(e.nces_title1_schoolwide, ''))) IN ('yes', '1-yes') THEN 'SCHOOLWIDE'
                    ELSE 'TARGETED_ASSISTANCE'
                END
            WHEN lower(trim(COALESCE(e.nces_title1, ''))) IN ('no', '2-no') THEN 'NON_TITLE_I'
            WHEN lower(trim(COALESCE(e.nces_title1_schoolwide, ''))) IN ('yes', '1-yes') THEN 'SCHOOLWIDE'
            WHEN lower(trim(COALESCE(e.nces_title1, ''))) IN ('na', 'n/a', '') THEN 'UNREPORTED'
            ELSE 'UNREPORTED'
        END AS title_i_status,
        CASE
            WHEN lower(trim(COALESCE(e.nces_charter, ''))) IN ('yes', '1-yes', '1', 'true', 't') THEN TRUE
            WHEN lower(trim(COALESCE(e.nces_charter, ''))) IN ('no', '2-no', '0', 'false', 'f') THEN FALSE
            ELSE NULL
        END AS nces_charter,
        CASE
            WHEN lower(trim(COALESCE(e.nces_magnet, ''))) IN ('yes', '1-yes', '1', 'true', 't') THEN TRUE
            WHEN lower(trim(COALESCE(e.nces_magnet, ''))) IN ('no', '2-no', '0', 'false', 'f') THEN FALSE
            ELSE NULL
        END AS nces_magnet,
        CASE
            WHEN upper(trim(COALESCE(e.nces_freelunch, ''))) IN ('', 'NA', 'NRD') THEN NULL
            WHEN regexp_replace(trim(e.nces_freelunch), '[,$ ]', '', 'g') ~ '^[-]?[0-9]+(\.[0-9]+)?$'
                THEN regexp_replace(trim(e.nces_freelunch), '[,$ ]', '', 'g')::numeric(14,2)::integer
            ELSE NULL
        END AS nces_freelunch,
        CASE
            WHEN upper(trim(COALESCE(e.nces_reducedlunch, ''))) IN ('', 'NA', 'NRD') THEN NULL
            WHEN regexp_replace(trim(e.nces_reducedlunch), '[,$ ]', '', 'g') ~ '^[-]?[0-9]+(\.[0-9]+)?$'
                THEN regexp_replace(trim(e.nces_reducedlunch), '[,$ ]', '', 'g')::numeric(14,2)::integer
            ELSE NULL
        END AS nces_reducedlunch,
        CASE
            WHEN upper(trim(COALESCE(e.pp_fed_raw_al, ''))) IN ('', 'NA', 'NRD') THEN NULL
            WHEN regexp_replace(trim(e.pp_fed_raw_al), '[,$ ]', '', 'g') ~ '^[-]?[0-9]+(\.[0-9]+)?$'
                THEN regexp_replace(trim(e.pp_fed_raw_al), '[,$ ]', '', 'g')::numeric(14,2)
            ELSE NULL
        END AS per_pupil_nces_raw,
        CASE
            WHEN upper(trim(COALESCE(e.pp_total_raw_al, ''))) IN ('', 'NA', 'NRD') THEN NULL
            WHEN regexp_replace(trim(e.pp_total_raw_al), '[,$ ]', '', 'g') ~ '^[-]?[0-9]+(\.[0-9]+)?$'
                THEN regexp_replace(trim(e.pp_total_raw_al), '[,$ ]', '', 'g')::numeric(14,2)
            ELSE NULL
        END AS per_pupil_total_raw,
        CASE
            WHEN upper(trim(COALESCE(e.pp_total_norm_nerds, ''))) IN ('', 'NA', 'NRD') THEN NULL
            WHEN regexp_replace(trim(e.pp_total_norm_nerds), '[,$ ]', '', 'g') ~ '^[-]?[0-9]+(\.[0-9]+)?$'
                THEN regexp_replace(trim(e.pp_total_norm_nerds), '[,$ ]', '', 'g')::numeric(14,2)
            ELSE NULL
        END AS per_pupil_total_norm_nerds,
        CASE
            WHEN upper(trim(COALESCE(e.pp_site_stloc_raw_al, ''))) IN ('', 'NA', 'NRD') THEN NULL
            WHEN regexp_replace(trim(e.pp_site_stloc_raw_al), '[,$ ]', '', 'g') ~ '^[-]?[0-9]+(\.[0-9]+)?$'
                THEN regexp_replace(trim(e.pp_site_stloc_raw_al), '[,$ ]', '', 'g')::numeric(14,2)::integer
            ELSE NULL
        END AS per_pupil_site_stloc_raw_al,
        CASE
            WHEN upper(trim(COALESCE(e.pp_site_fed_raw_al, ''))) IN ('', 'NA', 'NRD') THEN NULL
            WHEN regexp_replace(trim(e.pp_site_fed_raw_al), '[,$ ]', '', 'g') ~ '^[-]?[0-9]+(\.[0-9]+)?$'
                THEN regexp_replace(trim(e.pp_site_fed_raw_al), '[,$ ]', '', 'g')::numeric(14,2)::integer
            ELSE NULL
        END AS per_pupil_site_nces_raw_al,
        CASE
            WHEN upper(trim(COALESCE(e.pp_site_raw_al, ''))) IN ('', 'NA', 'NRD') THEN NULL
            WHEN regexp_replace(trim(e.pp_site_raw_al), '[,$ ]', '', 'g') ~ '^[-]?[0-9]+(\.[0-9]+)?$'
                THEN regexp_replace(trim(e.pp_site_raw_al), '[,$ ]', '', 'g')::numeric(14,2)::integer
            ELSE NULL
        END AS per_pupil_site_raw_al,
        CASE
            WHEN upper(trim(COALESCE(e.pp_centshare_stloc_raw_al, ''))) IN ('', 'NA', 'NRD') THEN NULL
            WHEN regexp_replace(trim(e.pp_centshare_stloc_raw_al), '[,$ ]', '', 'g') ~ '^[-]?[0-9]+(\.[0-9]+)?$'
                THEN regexp_replace(trim(e.pp_centshare_stloc_raw_al), '[,$ ]', '', 'g')::numeric(14,2)::integer
            ELSE NULL
        END AS per_pupil_centshare_stloc_raw_al,
        CASE
            WHEN upper(trim(COALESCE(e.pp_centshare_fed_raw_al, ''))) IN ('', 'NA', 'NRD') THEN NULL
            WHEN regexp_replace(trim(e.pp_centshare_fed_raw_al), '[,$ ]', '', 'g') ~ '^[-]?[0-9]+(\.[0-9]+)?$'
                THEN regexp_replace(trim(e.pp_centshare_fed_raw_al), '[,$ ]', '', 'g')::numeric(14,2)::integer
            ELSE NULL
        END AS per_pupil_centshare_nces_raw_al,
        CASE
            WHEN upper(trim(COALESCE(e.pp_centshare_raw_al, ''))) IN ('', 'NA', 'NRD') THEN NULL
            WHEN regexp_replace(trim(e.pp_centshare_raw_al), '[,$ ]', '', 'g') ~ '^[-]?[0-9]+(\.[0-9]+)?$'
                THEN regexp_replace(trim(e.pp_centshare_raw_al), '[,$ ]', '', 'g')::numeric(14,2)::integer
            ELSE NULL
        END AS per_pupil_centshare_raw_al,
        CASE
            WHEN trim(COALESCE(e.flag_nerds, '')) = '1' THEN TRUE
            WHEN trim(COALESCE(e.flag_nerds, '')) = '0' THEN FALSE
            ELSE NULL
        END AS flag_nerds,
        CASE
            WHEN trim(COALESCE(e.flag_f33, '')) = '1' THEN TRUE
            WHEN trim(COALESCE(e.flag_f33, '')) IN ('0', '-1') THEN FALSE
            ELSE NULL
        END AS flag_f33,
        e._source_file,
        e._ingested_at,
        ROW_NUMBER() OVER (
            PARTITION BY
                e.year,
                lower(trim(regexp_replace(e.distname, '[[:space:]]+', ' ', 'g'))),
                lower(trim(regexp_replace(e.schoolname, '[[:space:]]+', ' ', 'g')))
            ORDER BY e._ingested_at DESC NULLS LAST, e._source_file DESC NULLS LAST
        ) AS rn
    FROM staging.stg_school_edunomics e
)
INSERT INTO sandbox.fact_edunomics_review (
    school_year_label, year, dist_name, school_name,
    state_dist_id, state_school_id,
    ncesenroll, gradespan, level, enroll_raw,
    state_local_per_pupil, state_local_fund, nces_fund, nces_poverty,
    title_i_status, nces_charter, nces_magnet,
    nces_freelunch, nces_reducedlunch,
    per_pupil_nces_raw, per_pupil_total_raw, per_pupil_total_norm_nerds,
    per_pupil_site_stloc_raw_al, per_pupil_site_nces_raw_al, per_pupil_site_raw_al,
    per_pupil_centshare_stloc_raw_al, per_pupil_centshare_nces_raw_al, per_pupil_centshare_raw_al,
    flag_nerds, flag_f33
)
SELECT
    school_year_label, year, dist_name, school_name,
    state_dist_id, state_school_id,
    ncesenroll, gradespan, level, enroll_raw,
    state_local_per_pupil, state_local_fund, nces_fund, nces_poverty,
    title_i_status, nces_charter, nces_magnet,
    nces_freelunch, nces_reducedlunch,
    per_pupil_nces_raw, per_pupil_total_raw, per_pupil_total_norm_nerds,
    per_pupil_site_stloc_raw_al, per_pupil_site_nces_raw_al, per_pupil_site_raw_al,
    per_pupil_centshare_stloc_raw_al, per_pupil_centshare_nces_raw_al, per_pupil_centshare_raw_al,
    flag_nerds, flag_f33
FROM src
WHERE rn = 1;

WITH src AS (
    SELECT
        t.year::smallint AS year,
        trim(regexp_replace(t.system, '[[:space:]]+', ' ', 'g')) AS dist_name,
        trim(regexp_replace(t.school, '[[:space:]]+', ' ', 'g')) AS school_name,
        NULLIF(trim(t.educator_effectiveness_score), '') AS score,
        NULLIF(trim(t.atot_completion_rate_designation), '') AS atot_completion_rate_designation,
        CASE
            WHEN lower(trim(COALESCE(t.title_i_status, ''))) IN ('n/a', 'na', '') THEN 'UNREPORTED'
            WHEN lower(trim(COALESCE(t.title_i_status, ''))) LIKE '%non-title i%' THEN 'NON_TITLE_I'
            WHEN lower(trim(COALESCE(t.title_i_status, ''))) LIKE '%school%' THEN 'SCHOOLWIDE'
            WHEN lower(trim(COALESCE(t.title_i_status, ''))) LIKE '%target%' THEN 'TARGETED_ASSISTANCE'
            ELSE 'UNREPORTED'
        END AS title_i_status,
        CASE
            WHEN lower(trim(COALESCE(t.title_i_status, ''))) IN ('n/a', 'na', '') THEN 0
            ELSE 1
        END AS title_priority,
        t._source_file,
        t._ingested_at,
        ROW_NUMBER() OVER (
            PARTITION BY
                t.year::smallint,
                lower(trim(regexp_replace(t.system, '[[:space:]]+', ' ', 'g'))),
                lower(trim(regexp_replace(t.school, '[[:space:]]+', ' ', 'g')))
            ORDER BY
                CASE
                    WHEN lower(trim(COALESCE(t.title_i_status, ''))) IN ('n/a', 'na', '') THEN 0
                    ELSE 1
                END DESC,
                t._ingested_at DESC NULLS LAST,
                t._source_file DESC NULLS LAST
        ) AS rn
    FROM staging.stg_teacher_effectiveness t
)
INSERT INTO sandbox.fact_teacher_effectiveness_review (
    year, dist_name, school_name, score, atot_completion_rate_designation, title_i_status
)
SELECT
    year, dist_name, school_name, score, atot_completion_rate_designation, title_i_status
FROM src
WHERE rn = 1;

WITH src AS (
    SELECT
        t.year::smallint AS year,
        trim(regexp_replace(t.system, '[[:space:]]+', ' ', 'g')) AS dist_name,
        trim(regexp_replace(t.school, '[[:space:]]+', ' ', 'g')) AS school_name,
        g.canonical_value AS gender,
        r.canonical_value AS race,
        e.canonical_value AS ethnicity,
        COALESCE(NULLIF(trim(t.sub_population), ''), 'Unknown SubPopulation') AS sub_population,
        NULLIF(trim(t.total_count), '')::numeric(14,2) AS total_count,
        NULLIF(trim(t.experienced_count), '')::numeric(14,2) AS exp_count,
        NULLIF(trim(t.experienced_rate), '')::numeric(8,4) AS exp_rate,
        NULLIF(trim(t.inexperienced_count), '')::numeric(14,2) AS inexp_count,
        NULLIF(trim(t.inexperienced_rate), '')::numeric(8,4) AS inexp_rate,
        t._source_file,
        t._ingested_at,
        ROW_NUMBER() OVER (
            PARTITION BY
                t.year::smallint,
                lower(trim(regexp_replace(t.system, '[[:space:]]+', ' ', 'g'))),
                lower(trim(regexp_replace(t.school, '[[:space:]]+', ' ', 'g'))),
                g.canonical_value,
                r.canonical_value,
                e.canonical_value,
                COALESCE(NULLIF(trim(t.sub_population), ''), 'Unknown SubPopulation')
            ORDER BY t._ingested_at DESC NULLS LAST, t._source_file DESC NULLS LAST
        ) AS rn
    FROM staging.stg_teacher_experience t
    JOIN ref.gender_canonical g
      ON g.normalized_value = lower(trim(regexp_replace(t.gender, '[[:space:]]+', ' ', 'g')))
    JOIN ref.race_canonical r
      ON r.normalized_value = lower(trim(regexp_replace(t.race, '[[:space:]]+', ' ', 'g')))
    JOIN ref.ethnicity_canonical e
      ON e.normalized_value = lower(trim(regexp_replace(t.ethnicity, '[[:space:]]+', ' ', 'g')))
)
INSERT INTO sandbox.fact_teacher_experience_review (
    year, dist_name, school_name, gender, race, ethnicity, sub_population,
    total_count, exp_count, exp_rate, inexp_count, inexp_rate
)
SELECT
    year, dist_name, school_name, gender, race, ethnicity, sub_population,
    total_count, exp_count, exp_rate, inexp_count, inexp_rate
FROM src
WHERE rn = 1;

WITH src AS (
    SELECT
        t.year::smallint AS year,
        trim(regexp_replace(t.system, '[[:space:]]+', ' ', 'g')) AS dist_name,
        trim(regexp_replace(t.school, '[[:space:]]+', ' ', 'g')) AS school_name,
        g.canonical_value AS gender,
        r.canonical_value AS race,
        e.canonical_value AS ethnicity,
        COALESCE(NULLIF(trim(t.sub_population), ''), 'Unknown SubPopulation') AS sub_population,
        COALESCE(NULLIF(trim(t.degree_type), ''), 'Unknown Degree Type') AS degree_type,
        CASE
            WHEN upper(trim(COALESCE(t.credential_count, ''))) IN ('', 'NA', 'NRD', '*', '**', '~', '--', 'SUPP', 'SUPPRESSED') THEN NULL
            WHEN regexp_replace(trim(t.credential_count), '[,$ ]', '', 'g') ~ '^[-]?[0-9]+(\.[0-9]+)?$'
                THEN regexp_replace(trim(t.credential_count), '[,$ ]', '', 'g')::numeric(14,2)
            ELSE NULL
        END AS credential_count,
        CASE
            WHEN upper(trim(COALESCE(t.total_count, ''))) IN ('', 'NA', 'NRD', '*', '**', '~', '--', 'SUPP', 'SUPPRESSED') THEN NULL
            WHEN regexp_replace(trim(t.total_count), '[,$ ]', '', 'g') ~ '^[-]?[0-9]+(\.[0-9]+)?$'
                THEN regexp_replace(trim(t.total_count), '[,$ ]', '', 'g')::numeric(14,2)
            ELSE NULL
        END AS total_count,
        CASE
            WHEN upper(trim(COALESCE(t.credential_rate, ''))) IN ('', 'NA', 'NRD', '*', '**', '~', '--', 'SUPP', 'SUPPRESSED') THEN NULL
            WHEN regexp_replace(trim(t.credential_rate), '[,$ %]', '', 'g') ~ '^[-]?[0-9]+(\.[0-9]+)?$'
                THEN regexp_replace(trim(t.credential_rate), '[,$ %]', '', 'g')::numeric(8,4)
            ELSE NULL
        END AS credential_rate,
        t._source_file,
        t._ingested_at,
        ROW_NUMBER() OVER (
            PARTITION BY
                t.year::smallint,
                lower(trim(regexp_replace(t.system, '[[:space:]]+', ' ', 'g'))),
                lower(trim(regexp_replace(t.school, '[[:space:]]+', ' ', 'g'))),
                g.canonical_value,
                r.canonical_value,
                e.canonical_value,
                COALESCE(NULLIF(trim(t.sub_population), ''), 'Unknown SubPopulation'),
                COALESCE(NULLIF(trim(t.degree_type), ''), 'Unknown Degree Type')
            ORDER BY t._ingested_at DESC NULLS LAST, t._source_file DESC NULLS LAST
        ) AS rn
    FROM staging.stg_educator_credentials t
    JOIN ref.gender_canonical g
      ON g.normalized_value = lower(trim(regexp_replace(t.gender, '[[:space:]]+', ' ', 'g')))
    JOIN ref.race_canonical r
      ON r.normalized_value = lower(trim(regexp_replace(t.race, '[[:space:]]+', ' ', 'g')))
    JOIN ref.ethnicity_canonical e
      ON e.normalized_value = lower(trim(regexp_replace(t.ethnicity, '[[:space:]]+', ' ', 'g')))
    WHERE trim(COALESCE(t.year, '')) ~ '^[0-9]{4}$'
)
INSERT INTO sandbox.fact_educator_credentials_review (
    year, dist_name, school_name, gender, race, ethnicity, sub_population,
    degree_type, credential_count, total_count, credential_rate
)
SELECT
    year, dist_name, school_name, gender, race, ethnicity, sub_population,
    degree_type, credential_count, total_count, credential_rate
FROM src
WHERE rn = 1;

INSERT INTO sandbox.fact_educator_credentials_wide_review (
    year, dist_name, school_name, gender, race, ethnicity, sub_population,
    total_count_all_degree, credential_count_all_degree, credential_rate_all_degree,
    credential_count_six_year_class_aa, credential_rate_six_year_class_aa,
    credential_count_masters_degree_class_a, credential_rate_masters_degree_class_a,
    credential_count_bachelors_degree_class_b, credential_rate_bachelors_degree_class_b,
    credential_count_not_specified, credential_rate_not_specified,
    credential_count_emergency_certificates, credential_rate_emergency_certificates,
    credential_count_provisional_certificates, credential_rate_provisional_certificates
)
SELECT
    year,
    dist_name,
    school_name,
    gender,
    race,
    ethnicity,
    sub_population,
    MAX(CASE WHEN degree_type = 'All Degree' THEN total_count END) AS total_count_all_degree,
    MAX(CASE WHEN degree_type = 'All Degree' THEN credential_count END) AS credential_count_all_degree,
    MAX(CASE WHEN degree_type = 'All Degree' THEN credential_rate END) AS credential_rate_all_degree,
    MAX(CASE WHEN degree_type = 'Six-Year (Class AA)' THEN credential_count END) AS credential_count_six_year_class_aa,
    MAX(CASE WHEN degree_type = 'Six-Year (Class AA)' THEN credential_rate END) AS credential_rate_six_year_class_aa,
    MAX(CASE WHEN degree_type = 'Master''s Degree (Class A)' THEN credential_count END) AS credential_count_masters_degree_class_a,
    MAX(CASE WHEN degree_type = 'Master''s Degree (Class A)' THEN credential_rate END) AS credential_rate_masters_degree_class_a,
    MAX(CASE WHEN degree_type = 'Bachelor''s Degree (Class B)' THEN credential_count END) AS credential_count_bachelors_degree_class_b,
    MAX(CASE WHEN degree_type = 'Bachelor''s Degree (Class B)' THEN credential_rate END) AS credential_rate_bachelors_degree_class_b,
    MAX(CASE WHEN degree_type = 'Not Specified' THEN credential_count END) AS credential_count_not_specified,
    MAX(CASE WHEN degree_type = 'Not Specified' THEN credential_rate END) AS credential_rate_not_specified,
    MAX(CASE WHEN degree_type = 'Emergency Certificates' THEN credential_count END) AS credential_count_emergency_certificates,
    MAX(CASE WHEN degree_type = 'Emergency Certificates' THEN credential_rate END) AS credential_rate_emergency_certificates,
    MAX(CASE WHEN degree_type = 'Provisional Certificates' THEN credential_count END) AS credential_count_provisional_certificates,
    MAX(CASE WHEN degree_type = 'Provisional Certificates' THEN credential_rate END) AS credential_rate_provisional_certificates
FROM sandbox.fact_educator_credentials_review
GROUP BY year, dist_name, school_name, gender, race, ethnicity, sub_population;

WITH src AS (
    SELECT
        t.year::smallint AS year,
        trim(regexp_replace(t.system, '[[:space:]]+', ' ', 'g')) AS dist_name,
        trim(regexp_replace(t.school, '[[:space:]]+', ' ', 'g')) AS school_name,
        COALESCE(NULLIF(trim(t.grade), ''), 'Unknown Grade') AS grade,
        g.canonical_value AS gender,
        r.canonical_value AS race,
        e.canonical_value AS ethnicity,
        COALESCE(NULLIF(trim(t.sub_population), ''), 'Unknown SubPopulation') AS sub_population,
        CASE
            WHEN upper(trim(COALESCE(t.student_count, ''))) IN ('', 'NA', 'NRD', '*', '**', '~', '--', 'SUPP', 'SUPPRESSED') THEN NULL
            WHEN regexp_replace(trim(t.student_count), '[,$ ]', '', 'g') ~ '^[-]?[0-9]+(\.[0-9]+)?$'
                THEN regexp_replace(trim(t.student_count), '[,$ ]', '', 'g')::numeric(14,2)
            ELSE NULL
        END AS student_count,
        CASE
            WHEN upper(trim(COALESCE(t.graduates, ''))) IN ('', 'NA', 'NRD', '*', '**', '~', '--', 'SUPP', 'SUPPRESSED') THEN NULL
            WHEN regexp_replace(trim(t.graduates), '[,$ ]', '', 'g') ~ '^[-]?[0-9]+(\.[0-9]+)?$'
                THEN regexp_replace(trim(t.graduates), '[,$ ]', '', 'g')::numeric(14,2)
            ELSE NULL
        END AS graduates,
        CASE
            WHEN upper(trim(COALESCE(t.graduation_percent, ''))) IN ('', 'NA', 'NRD', '*', '**', '~', '--', 'SUPP', 'SUPPRESSED') THEN NULL
            WHEN regexp_replace(trim(t.graduation_percent), '[,$ %]', '', 'g') ~ '^[-]?[0-9]+(\.[0-9]+)?$'
                THEN regexp_replace(trim(t.graduation_percent), '[,$ %]', '', 'g')::numeric(8,4)
            ELSE NULL
        END AS graduation_percent,
        CASE
            WHEN upper(trim(COALESCE(t.ccr_attainment, ''))) IN ('', 'NA', 'NRD', '*', '**', '~', '--', 'SUPP', 'SUPPRESSED') THEN NULL
            WHEN regexp_replace(trim(t.ccr_attainment), '[,$ ]', '', 'g') ~ '^[-]?[0-9]+(\.[0-9]+)?$'
                THEN regexp_replace(trim(t.ccr_attainment), '[,$ ]', '', 'g')::numeric(14,2)
            ELSE NULL
        END AS ccr_attainment,
        CASE
            WHEN upper(trim(COALESCE(t.ccr_attainment_percent, ''))) IN ('', 'NA', 'NRD', '*', '**', '~', '--', 'SUPP', 'SUPPRESSED') THEN NULL
            WHEN regexp_replace(trim(t.ccr_attainment_percent), '[,$ %]', '', 'g') ~ '^[-]?[0-9]+(\.[0-9]+)?$'
                THEN regexp_replace(trim(t.ccr_attainment_percent), '[,$ %]', '', 'g')::numeric(8,4)
            ELSE NULL
        END AS ccr_attainment_percent,
        t._source_file,
        t._ingested_at,
        ROW_NUMBER() OVER (
            PARTITION BY
                t.year::smallint,
                lower(trim(regexp_replace(t.system, '[[:space:]]+', ' ', 'g'))),
                lower(trim(regexp_replace(t.school, '[[:space:]]+', ' ', 'g'))),
                COALESCE(NULLIF(trim(t.grade), ''), 'Unknown Grade'),
                g.canonical_value,
                r.canonical_value,
                e.canonical_value,
                COALESCE(NULLIF(trim(t.sub_population), ''), 'Unknown SubPopulation')
            ORDER BY t._ingested_at DESC NULLS LAST, t._source_file DESC NULLS LAST
        ) AS rn
    FROM staging.stg_graduation_rate t
    JOIN ref.gender_canonical g
      ON g.normalized_value = lower(trim(regexp_replace(t.gender, '[[:space:]]+', ' ', 'g')))
    JOIN ref.race_canonical r
      ON r.normalized_value = lower(trim(regexp_replace(t.race, '[[:space:]]+', ' ', 'g')))
    JOIN ref.ethnicity_canonical e
      ON e.normalized_value = lower(trim(regexp_replace(t.ethnicity, '[[:space:]]+', ' ', 'g')))
    WHERE trim(COALESCE(t.year, '')) ~ '^[0-9]{4}$'
)
INSERT INTO sandbox.fact_graduation_rate_review (
    year, dist_name, school_name, grade, gender, race, ethnicity, sub_population,
    student_count, graduates, graduation_percent, ccr_attainment, ccr_attainment_percent
)
SELECT
    year, dist_name, school_name, grade, gender, race, ethnicity, sub_population,
    student_count, graduates, graduation_percent, ccr_attainment, ccr_attainment_percent
FROM src
WHERE rn = 1;

INSERT INTO sandbox.fact_graduation_rate_wide_review (
    year, dist_name, school_name,
    student_count, graduates, graduation_percent, ccr_attainment, ccr_attainment_percent
)
SELECT
    year,
    dist_name,
    school_name,
    MAX(student_count) AS student_count,
    MAX(graduates) AS graduates,
    MAX(graduation_percent) AS graduation_percent,
    MAX(ccr_attainment) AS ccr_attainment,
    MAX(ccr_attainment_percent) AS ccr_attainment_percent
FROM sandbox.fact_graduation_rate_review
WHERE grade = 'All Grades'
  AND gender = 'All Gender'
  AND race = 'All Race'
  AND ethnicity = 'All Ethnicity'
  AND sub_population = 'All SubPopulation'
GROUP BY year, dist_name, school_name;

CREATE INDEX idx_fact_accountability_review_school_year
  ON sandbox.fact_accountability_review (year, dist_name, school_name);
CREATE INDEX idx_fact_edunomics_review_school_year
  ON sandbox.fact_edunomics_review (year, dist_name, school_name);
CREATE INDEX idx_fact_teacher_effect_review_school_year
  ON sandbox.fact_teacher_effectiveness_review (year, dist_name, school_name);
CREATE INDEX idx_fact_teacher_exp_review_school_year
  ON sandbox.fact_teacher_experience_review (year, dist_name, school_name);
CREATE INDEX idx_fact_educator_credentials_review_school_year
  ON sandbox.fact_educator_credentials_review (year, dist_name, school_name);
CREATE INDEX idx_fact_educator_credentials_wide_review_school_year
  ON sandbox.fact_educator_credentials_wide_review (year, dist_name, school_name);
CREATE INDEX idx_fact_graduation_rate_review_school_year
  ON sandbox.fact_graduation_rate_review (year, dist_name, school_name);
CREATE INDEX idx_fact_graduation_rate_wide_review_school_year
  ON sandbox.fact_graduation_rate_wide_review (year, dist_name, school_name);

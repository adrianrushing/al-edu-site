-- Upsert reviewed geographic tables into core.
-- Run after sandbox_geo_review_models.sql and core_load_review_to_core.sql.

BEGIN;

CREATE SCHEMA IF NOT EXISTS core;

DROP VIEW IF EXISTS core.vw_school_year_geo_bridge;
DROP VIEW IF EXISTS core.vw_school_year_geo_opportunity;
DROP VIEW IF EXISTS core.vw_school_year_geo_population;
DROP VIEW IF EXISTS core.vw_school_year_geo_context;

DROP TABLE IF EXISTS core.fact_geo_population_county;
DROP TABLE IF EXISTS core.fact_geo_opportunity_county;
ALTER TABLE IF EXISTS core.dim_geo_tract
    DROP CONSTRAINT IF EXISTS dim_geo_tract_county_fips_fkey;
ALTER TABLE IF EXISTS core.bridge_school_geo_county
    DROP CONSTRAINT IF EXISTS bridge_school_geo_county_county_fips_fkey;
DROP TABLE IF EXISTS core.dim_geo_county;
DROP TABLE IF EXISTS core.fact_school_outcomes_long;
DROP TABLE IF EXISTS core.bridge_school_geo_county;
DROP TABLE IF EXISTS core.fact_school_outcomes_wide;
DROP TABLE IF EXISTS core.fact_school_outcomes_demographic;

CREATE TABLE IF NOT EXISTS core.dim_geo_tract (
    geoid10        CHAR(11) PRIMARY KEY,
    state_fips     CHAR(2) NOT NULL,
    state_usps     CHAR(2) NOT NULL,
    state_name     TEXT NOT NULL,
    county_fips    CHAR(5) NOT NULL,
    county_name    TEXT,
    metro_fips     CHAR(5),
    metro_name     TEXT,
    metro_type     TEXT,
    in100          SMALLINT,
    primary_ruca   SMALLINT,
    _created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS core.fact_geo_population (
    geoid10            CHAR(11) NOT NULL REFERENCES core.dim_geo_tract(geoid10),
    year               SMALLINT NOT NULL,
    population_group   TEXT NOT NULL REFERENCES ref.geo_population_group(population_group),
    population_count   DOUBLE PRECISION,
    _created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_core_fact_geo_population PRIMARY KEY (geoid10, year, population_group)
);

CREATE TABLE IF NOT EXISTS core.fact_geo_opportunity (
    geoid10             CHAR(11) NOT NULL REFERENCES core.dim_geo_tract(geoid10),
    year                SMALLINT NOT NULL,
    metric_code         TEXT NOT NULL REFERENCES ref.geo_metric(metric_code),
    norm_scope          TEXT NOT NULL REFERENCES ref.geo_norm_scope(norm_scope),
    opportunity_level   TEXT REFERENCES ref.geo_opportunity_level(canonical_value),
    opportunity_score   SMALLINT,
    opportunity_zscore  DOUBLE PRECISION,
    _created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_core_fact_geo_opportunity PRIMARY KEY (geoid10, year, metric_code, norm_scope)
);

CREATE TABLE IF NOT EXISTS core.fact_geo_population_county (
    county_fips         CHAR(5) NOT NULL,
    year                SMALLINT NOT NULL,
    population_group    TEXT NOT NULL REFERENCES ref.geo_population_group(population_group),
    population_count    DOUBLE PRECISION,
    _created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_core_fact_geo_population_county PRIMARY KEY (county_fips, year, population_group)
);

CREATE TABLE IF NOT EXISTS core.fact_geo_opportunity_county (
    county_fips               CHAR(5) NOT NULL,
    year                      SMALLINT NOT NULL,
    metric_code               TEXT NOT NULL REFERENCES ref.geo_metric(metric_code),
    norm_scope                TEXT NOT NULL REFERENCES ref.geo_norm_scope(norm_scope),
    opportunity_level_mode    TEXT REFERENCES ref.geo_opportunity_level(canonical_value),
    opportunity_score_avg     DOUBLE PRECISION,
    opportunity_zscore_avg    DOUBLE PRECISION,
    tract_count               INTEGER,
    _created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_core_fact_geo_opportunity_county PRIMARY KEY (county_fips, year, metric_code, norm_scope)
);

CREATE TABLE IF NOT EXISTS core.bridge_school_geo_county (
    school_key          BIGINT NOT NULL,
    school_year_start   SMALLINT NOT NULL,
    county_fips         CHAR(5),
    county_name         TEXT,
    match_method        TEXT,
    match_confidence    NUMERIC(4,3),
    strict_null_reason  TEXT,
    _created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_core_bridge_school_geo_county PRIMARY KEY (school_key, school_year_start),
    CONSTRAINT fk_core_bridge_school_geo_county_school FOREIGN KEY (school_key, school_year_start)
      REFERENCES core.dim_school_info(school_key, school_year_start)
);

CREATE TABLE IF NOT EXISTS core.fact_school_outcomes_wide (
    school_key          BIGINT NOT NULL,
    year                SMALLINT NOT NULL,
    ach_all             DOUBLE PRECISION,
    grw_all             DOUBLE PRECISION,
    abs_all             DOUBLE PRECISION,
    coi                 DOUBLE PRECISION,
    coi_ed              DOUBLE PRECISION,
    coi_he              DOUBLE PRECISION,
    coi_st              DOUBLE PRECISION,
    ppe                 DOUBLE PRECISION,
    _created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_core_fact_school_outcomes_wide PRIMARY KEY (school_key, year),
    CONSTRAINT fk_core_fact_school_outcomes_school_year FOREIGN KEY (school_key, year)
      REFERENCES core.dim_school_info(school_key, school_year_start)
);

CREATE TABLE IF NOT EXISTS core.fact_school_outcomes_demographic (
    school_key          BIGINT NOT NULL,
    year                SMALLINT NOT NULL,
    enrollment          INTEGER,
    ach_all             DOUBLE PRECISION,
    grw_all             DOUBLE PRECISION,
    abs_all             DOUBLE PRECISION,
    ach_ecd             DOUBLE PRECISION,
    grw_ecd             DOUBLE PRECISION,
    abs_ecd             DOUBLE PRECISION,
    ach_esl             DOUBLE PRECISION,
    grw_esl             DOUBLE PRECISION,
    abs_esl             DOUBLE PRECISION,
    ach_asian           DOUBLE PRECISION,
    grw_asian           DOUBLE PRECISION,
    abs_asian           DOUBLE PRECISION,
    ach_black           DOUBLE PRECISION,
    grw_black           DOUBLE PRECISION,
    abs_black           DOUBLE PRECISION,
    ach_hsp             DOUBLE PRECISION,
    grw_hsp             DOUBLE PRECISION,
    abs_hsp             DOUBLE PRECISION,
    ach_white           DOUBLE PRECISION,
    grw_white           DOUBLE PRECISION,
    abs_white           DOUBLE PRECISION,
    ach_other           DOUBLE PRECISION,
    grw_other           DOUBLE PRECISION,
    abs_other           DOUBLE PRECISION,
    _created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_core_fact_school_outcomes_demographic PRIMARY KEY (school_key, year),
    CONSTRAINT fk_core_fact_school_outcomes_demographic_school FOREIGN KEY (school_key)
      REFERENCES core.dim_school_info(school_key)
);

INSERT INTO core.dim_geo_tract (
    geoid10,
    state_fips,
    state_usps,
    state_name,
    county_fips,
    county_name,
    metro_fips,
    metro_name,
    metro_type,
    in100,
    primary_ruca,
    _created_at,
    _updated_at
)
SELECT
    geoid10,
    state_fips,
    state_usps,
    state_name,
    county_fips,
    county_name,
    metro_fips,
    metro_name,
    metro_type,
    in100,
    primary_ruca,
    _created_at,
    _updated_at
FROM sandbox.dim_geo_tract_review
ON CONFLICT (geoid10) DO UPDATE SET
    state_fips   = EXCLUDED.state_fips,
    state_usps   = EXCLUDED.state_usps,
    state_name   = EXCLUDED.state_name,
    county_fips  = EXCLUDED.county_fips,
    county_name  = EXCLUDED.county_name,
    metro_fips   = EXCLUDED.metro_fips,
    metro_name   = EXCLUDED.metro_name,
    metro_type   = EXCLUDED.metro_type,
    in100        = EXCLUDED.in100,
    primary_ruca = EXCLUDED.primary_ruca,
    _updated_at  = now();

INSERT INTO core.fact_geo_population (
    geoid10,
    year,
    population_group,
    population_count,
    _created_at,
    _updated_at
)
SELECT
    geoid10,
    year,
    population_group,
    population_count,
    _created_at,
    _updated_at
FROM sandbox.fact_geo_population_review
ON CONFLICT (geoid10, year, population_group) DO UPDATE SET
    population_count = EXCLUDED.population_count,
    _updated_at      = now();

INSERT INTO core.fact_geo_opportunity (
    geoid10,
    year,
    metric_code,
    norm_scope,
    opportunity_level,
    opportunity_score,
    opportunity_zscore,
    _created_at,
    _updated_at
)
SELECT
    geoid10,
    year,
    metric_code,
    norm_scope,
    opportunity_level,
    opportunity_score,
    opportunity_zscore,
    _created_at,
    _updated_at
FROM sandbox.fact_geo_opportunity_review
ON CONFLICT (geoid10, year, metric_code, norm_scope) DO UPDATE SET
    opportunity_level  = EXCLUDED.opportunity_level,
    opportunity_score  = EXCLUDED.opportunity_score,
    opportunity_zscore = EXCLUDED.opportunity_zscore,
    _updated_at        = now();

INSERT INTO core.fact_geo_population_county (
    county_fips,
    year,
    population_group,
    population_count,
    _created_at,
    _updated_at
)
SELECT
    county_fips,
    year,
    population_group,
    population_count,
    _created_at,
    _updated_at
FROM sandbox.fact_geo_population_county_review
ON CONFLICT (county_fips, year, population_group) DO UPDATE SET
    population_count = EXCLUDED.population_count,
    _updated_at      = now();

INSERT INTO core.fact_geo_opportunity_county (
    county_fips,
    year,
    metric_code,
    norm_scope,
    opportunity_level_mode,
    opportunity_score_avg,
    opportunity_zscore_avg,
    tract_count,
    _created_at,
    _updated_at
)
SELECT
    county_fips,
    year,
    metric_code,
    norm_scope,
    opportunity_level_mode,
    opportunity_score_avg,
    opportunity_zscore_avg,
    tract_count,
    _created_at,
    _updated_at
FROM sandbox.fact_geo_opportunity_county_review
ON CONFLICT (county_fips, year, metric_code, norm_scope) DO UPDATE SET
    opportunity_level_mode = EXCLUDED.opportunity_level_mode,
    opportunity_score_avg  = EXCLUDED.opportunity_score_avg,
    opportunity_zscore_avg = EXCLUDED.opportunity_zscore_avg,
    tract_count            = EXCLUDED.tract_count,
    _updated_at            = now();


INSERT INTO core.bridge_school_geo_county (
    school_key,
    school_year_start,
    county_fips,
    county_name,
    match_method,
    match_confidence,
    strict_null_reason,
    _created_at,
    _updated_at
)
SELECT
    b.school_key,
    b.school_year_start,
    b.county_fips,
    b.county_name,
    b.match_method,
    b.match_confidence,
    b.strict_null_reason,
    b._created_at,
    b._updated_at
FROM sandbox.bridge_school_geo_county_review b
JOIN core.dim_school_info d
  ON d.school_key = b.school_key
 AND d.school_year_start = b.school_year_start
ON CONFLICT (school_key, school_year_start) DO UPDATE SET
    school_year_start  = EXCLUDED.school_year_start,
    county_fips        = EXCLUDED.county_fips,
    county_name        = EXCLUDED.county_name,
    match_method       = EXCLUDED.match_method,
    match_confidence   = EXCLUDED.match_confidence,
    strict_null_reason = EXCLUDED.strict_null_reason,
    _updated_at        = now();

INSERT INTO core.fact_school_outcomes_wide (
    school_key,
    year,
    ach_all,
    grw_all,
    abs_all,
    coi,
    coi_ed,
    coi_he,
    coi_st,
    ppe,
    _created_at,
    _updated_at
)
SELECT
    d.school_key,
    s.year,
    s.ach_all,
    s.grw_all,
    s.abs_all,
    s.coi,
    s.coi_ed,
    s.coi_he,
    s.coi_st,
    s.ppe,
    s._created_at,
    s._updated_at
FROM sandbox.fact_school_outcomes_wide_review s
JOIN core.dim_school_info d
  ON d.school_year_start = s.year
 AND lower(trim(regexp_replace(d.dist_name, '[[:space:]]+', ' ', 'g'))) = lower(trim(regexp_replace(s.dist_name, '[[:space:]]+', ' ', 'g')))
 AND lower(trim(regexp_replace(d.school_name, '[[:space:]]+', ' ', 'g'))) = lower(trim(regexp_replace(s.school_name, '[[:space:]]+', ' ', 'g')))
ON CONFLICT (school_key, year) DO UPDATE SET
    ach_all    = EXCLUDED.ach_all,
    grw_all    = EXCLUDED.grw_all,
    abs_all    = EXCLUDED.abs_all,
    coi        = EXCLUDED.coi,
    coi_ed     = EXCLUDED.coi_ed,
    coi_he     = EXCLUDED.coi_he,
    coi_st     = EXCLUDED.coi_st,
    ppe        = EXCLUDED.ppe,
    _updated_at = now();

INSERT INTO core.fact_school_outcomes_demographic (
    school_key,
    year,
    enrollment,
    ach_all,
    grw_all,
    abs_all,
    ach_ecd,
    grw_ecd,
    abs_ecd,
    ach_esl,
    grw_esl,
    abs_esl,
    ach_asian,
    grw_asian,
    abs_asian,
    ach_black,
    grw_black,
    abs_black,
    ach_hsp,
    grw_hsp,
    abs_hsp,
    ach_white,
    grw_white,
    abs_white,
    ach_other,
    grw_other,
    abs_other,
    _created_at,
    _updated_at
)
SELECT
    d.school_key,
    s.year,
    s.enrollment,
    s.ach_all,
    s.grw_all,
    s.abs_all,
    s.ach_ecd,
    s.grw_ecd,
    s.abs_ecd,
    s.ach_esl,
    s.grw_esl,
    s.abs_esl,
    s.ach_asian,
    s.grw_asian,
    s.abs_asian,
    s.ach_black,
    s.grw_black,
    s.abs_black,
    s.ach_hsp,
    s.grw_hsp,
    s.abs_hsp,
    s.ach_white,
    s.grw_white,
    s.abs_white,
    s.ach_other,
    s.grw_other,
    s.abs_other,
    now(),
    now()
FROM sandbox.fact_school_outcomes_demographic_review s
JOIN core.dim_school_info d
  ON d.school_year_start = s.year
 AND lower(trim(regexp_replace(d.dist_name, '[[:space:]]+', ' ', 'g'))) = lower(trim(regexp_replace(s.dist_name, '[[:space:]]+', ' ', 'g')))
 AND lower(trim(regexp_replace(d.school_name, '[[:space:]]+', ' ', 'g'))) = lower(trim(regexp_replace(s.school_name, '[[:space:]]+', ' ', 'g')))
ON CONFLICT (school_key, year) DO UPDATE SET
    enrollment = EXCLUDED.enrollment,
    ach_all    = EXCLUDED.ach_all,
    grw_all    = EXCLUDED.grw_all,
    abs_all    = EXCLUDED.abs_all,
    ach_ecd    = EXCLUDED.ach_ecd,
    grw_ecd    = EXCLUDED.grw_ecd,
    abs_ecd    = EXCLUDED.abs_ecd,
    ach_esl    = EXCLUDED.ach_esl,
    grw_esl    = EXCLUDED.grw_esl,
    abs_esl    = EXCLUDED.abs_esl,
    ach_asian  = EXCLUDED.ach_asian,
    grw_asian  = EXCLUDED.grw_asian,
    abs_asian  = EXCLUDED.abs_asian,
    ach_black  = EXCLUDED.ach_black,
    grw_black  = EXCLUDED.grw_black,
    abs_black  = EXCLUDED.abs_black,
    ach_hsp    = EXCLUDED.ach_hsp,
    grw_hsp    = EXCLUDED.grw_hsp,
    abs_hsp    = EXCLUDED.abs_hsp,
    ach_white  = EXCLUDED.ach_white,
    grw_white  = EXCLUDED.grw_white,
    abs_white  = EXCLUDED.abs_white,
    ach_other  = EXCLUDED.ach_other,
    grw_other  = EXCLUDED.grw_other,
    abs_other  = EXCLUDED.abs_other,
    _updated_at = now();


CREATE INDEX IF NOT EXISTS idx_core_dim_geo_tract_county
  ON core.dim_geo_tract (county_fips);
CREATE INDEX IF NOT EXISTS idx_core_fact_geo_population_year
  ON core.fact_geo_population (year, population_group);
CREATE INDEX IF NOT EXISTS idx_core_fact_geo_opportunity_year
  ON core.fact_geo_opportunity (year, metric_code, norm_scope);
CREATE INDEX IF NOT EXISTS idx_core_bridge_school_geo_county_reason
  ON core.bridge_school_geo_county (school_year_start, strict_null_reason);
CREATE INDEX IF NOT EXISTS idx_core_fact_school_outcomes_wide_year
  ON core.fact_school_outcomes_wide (year);
CREATE INDEX IF NOT EXISTS idx_core_fact_school_outcomes_demographic_year
  ON core.fact_school_outcomes_demographic (year);

CREATE INDEX IF NOT EXISTS idx_core_fact_geo_population_county_year
  ON core.fact_geo_population_county (year, population_group);
CREATE INDEX IF NOT EXISTS idx_core_fact_geo_opportunity_county_year
  ON core.fact_geo_opportunity_county (year, metric_code, norm_scope);

CREATE VIEW core.vw_school_year_geo_bridge AS
SELECT
    d.school_key,
    d.school_year_start AS year,
    d.state_code,
    d.dist_name,
    d.school_name,
    b.county_fips,
    b.county_name,
    b.match_method,
    b.match_confidence,
    b.strict_null_reason
FROM core.dim_school_info d
LEFT JOIN core.bridge_school_geo_county b
  ON b.school_key = d.school_key
 AND b.school_year_start = d.school_year_start;

CREATE VIEW core.vw_school_year_geo_opportunity AS
SELECT
    sb.school_key,
    sb.year,
    sb.state_code,
    sb.dist_name,
    sb.school_name,
    sb.county_fips,
    sb.county_name,
    go.metric_code,
    go.norm_scope,
    go.opportunity_level_mode,
    go.opportunity_score_avg,
    go.opportunity_zscore_avg,
    go.tract_count
FROM core.vw_school_year_geo_bridge sb
LEFT JOIN core.fact_geo_opportunity_county go
  ON go.county_fips = sb.county_fips
 AND go.year = sb.year;

CREATE VIEW core.vw_school_year_geo_population AS
SELECT
    sb.school_key,
    sb.year,
    sb.state_code,
    sb.dist_name,
    sb.school_name,
    sb.county_fips,
    sb.county_name,
    gp.population_group,
    gp.population_count
FROM core.vw_school_year_geo_bridge sb
LEFT JOIN core.fact_geo_population_county gp
  ON gp.county_fips = sb.county_fips
 AND gp.year = sb.year;

CREATE VIEW core.vw_school_year_geo_context AS
SELECT
    sy.school_key,
    sy.school_year_start AS year,
    sy.school_year_label,
    st.state_code,
    st.department_name,
    d.district_name,
    s.school_name,
    s.state_school_id,
    s.nces_id,
    s.nces_geo_id,
    s.census_id,
    s.nces_charter,
    s.nces_magnet,
    s.nces_address,
    s.nces_city,
    s.nces_zip,
    b.county_fips,
    b.county_name,
    b.match_method,
    b.match_confidence,
    b.strict_null_reason
FROM core.bridge_school_year sy
JOIN core.dim_school s ON s.school_key = sy.school_key
JOIN core.dim_district d ON d.district_key = s.district_key
JOIN core.dim_state st ON st.state_key = d.state_key
LEFT JOIN core.bridge_school_geo_county b
  ON b.school_key = sy.school_key
 AND b.school_year_start = sy.school_year_start;

COMMIT;

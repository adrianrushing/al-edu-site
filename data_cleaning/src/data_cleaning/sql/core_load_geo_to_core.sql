-- Upsert reviewed geographic tables into core.
-- Run after sandbox_geo_review_models.sql and core_load_review_to_core.sql.

BEGIN;

CREATE SCHEMA IF NOT EXISTS core;

DROP TABLE IF EXISTS core.fact_geo_population_county;
DROP TABLE IF EXISTS core.fact_geo_opportunity_county;
ALTER TABLE IF EXISTS core.dim_geo_tract
    DROP CONSTRAINT IF EXISTS dim_geo_tract_county_fips_fkey;
ALTER TABLE IF EXISTS core.bridge_school_geo_county
    DROP CONSTRAINT IF EXISTS bridge_school_geo_county_county_fips_fkey;
DROP TABLE IF EXISTS core.dim_geo_county;
DROP TABLE IF EXISTS core.fact_school_outcomes_long;

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

CREATE TABLE IF NOT EXISTS core.bridge_school_geo_county (
    school_key          BIGINT PRIMARY KEY REFERENCES core.dim_school_info(school_key),
    school_year_start   SMALLINT NOT NULL,
    county_fips         CHAR(5),
    county_name         TEXT,
    match_method        TEXT,
    match_confidence    NUMERIC(4,3),
    strict_null_reason  TEXT,
    _created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS core.fact_school_outcomes_wide (
    school_key          BIGINT NOT NULL REFERENCES core.dim_school_info(school_key),
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
    CONSTRAINT pk_core_fact_school_outcomes_wide PRIMARY KEY (school_key, year)
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
ON CONFLICT (school_key) DO UPDATE SET
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

COMMIT;

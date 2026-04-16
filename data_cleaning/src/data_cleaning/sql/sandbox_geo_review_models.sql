-- Build and populate AL geographic + outcomes review tables in sandbox.
-- Uses strict school-county linkage with hand-match NCES overrides first.

DROP TABLE IF EXISTS sandbox.bridge_school_geo_county_review;
DROP TABLE IF EXISTS sandbox.ref_al_district_to_county_review;
DROP TABLE IF EXISTS sandbox.ref_school_identity_crosswalk_review;
DROP TABLE IF EXISTS sandbox.fact_geo_opportunity_review;
DROP TABLE IF EXISTS sandbox.fact_geo_population_review;
DROP TABLE IF EXISTS sandbox.fact_school_outcomes_wide_review;
DROP TABLE IF EXISTS sandbox.dim_geo_tract_review;

CREATE TABLE sandbox.dim_geo_tract_review (
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


CREATE TABLE sandbox.fact_geo_population_review (
    geoid10            CHAR(11) NOT NULL,
    year               SMALLINT NOT NULL,
    population_group   TEXT NOT NULL,
    population_count   DOUBLE PRECISION,
    _created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_fact_geo_population_review PRIMARY KEY (geoid10, year, population_group)
);

CREATE TABLE sandbox.fact_geo_opportunity_review (
    geoid10             CHAR(11) NOT NULL,
    year                SMALLINT NOT NULL,
    metric_code         TEXT NOT NULL,
    norm_scope          TEXT NOT NULL,
    opportunity_level   TEXT,
    opportunity_score   SMALLINT,
    opportunity_zscore  DOUBLE PRECISION,
    _created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_fact_geo_opportunity_review PRIMARY KEY (geoid10, year, metric_code, norm_scope)
);


CREATE TABLE sandbox.bridge_school_geo_county_review (
    school_key          BIGINT PRIMARY KEY,
    school_year_start   SMALLINT NOT NULL,
    dist_name           TEXT NOT NULL,
    county_fips         CHAR(5),
    county_name         TEXT,
    match_method        TEXT,
    match_confidence    NUMERIC(4,3),
    strict_null_reason  TEXT,
    _created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE sandbox.ref_al_district_to_county_review (
    nces_admin_id  CHAR(7) NOT NULL,
    county_fips    CHAR(5) NOT NULL,
    county_name    TEXT NOT NULL,
    CONSTRAINT pk_ref_al_district_to_county_review PRIMARY KEY (nces_admin_id, county_fips)
);

CREATE TABLE sandbox.ref_school_identity_crosswalk_review (
    school_name              TEXT NOT NULL,
    system_name              TEXT,
    ncessch                  CHAR(12) NOT NULL,
    match_method             TEXT NOT NULL,
    priority                 INTEGER NOT NULL,
    school_name_normalized   TEXT NOT NULL,
    system_name_normalized   TEXT NOT NULL,
    CONSTRAINT pk_ref_school_identity_crosswalk_review
      PRIMARY KEY (school_name_normalized, system_name_normalized, ncessch, match_method)
);

CREATE TABLE sandbox.fact_school_outcomes_wide_review (
    year                    SMALLINT NOT NULL,
    dist_name               TEXT NOT NULL,
    school_name             TEXT NOT NULL,
    ncessch                 CHAR(12),
    county_fips             CHAR(5),
    ach_all                 DOUBLE PRECISION,
    grw_all                 DOUBLE PRECISION,
    abs_all                 DOUBLE PRECISION,
    coi                     DOUBLE PRECISION,
    coi_ed                  DOUBLE PRECISION,
    coi_he                  DOUBLE PRECISION,
    coi_st                  DOUBLE PRECISION,
    ppe                     DOUBLE PRECISION,
    _created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_fact_school_outcomes_wide_review
      PRIMARY KEY (year, dist_name, school_name)
);


DROP TABLE IF EXISTS _district_to_county_raw;

CREATE TEMP TABLE _district_to_county_raw (
    state_postal_code     TEXT,
    state_fips            TEXT,
    district_id_number    TEXT,
    school_district_name  TEXT,
    county_names          TEXT,
    county_fips           TEXT
);

\copy _district_to_county_raw FROM 'flat_data/in/raw_data/crosswalks/district_to_county.csv' WITH (FORMAT csv, HEADER true)

CREATE TEMP TABLE _school_identity_crosswalk_raw (
    school_name   TEXT,
    system_name   TEXT,
    ncessch       TEXT,
    match_method  TEXT,
    priority      TEXT
);

\copy _school_identity_crosswalk_raw FROM 'flat_data/in/raw_data/crosswalks/generated/school_identity_crosswalk_prepared.csv' WITH (FORMAT csv, HEADER true)

CREATE TEMP TABLE _al_sch24_raw (
    year_val    TEXT,
    system_name TEXT,
    school_name TEXT,
    ncessch     TEXT,
    countyid    TEXT,
    ach_all     TEXT,
    grw_all     TEXT,
    abs_all     TEXT,
    ach_ecd     TEXT,
    grw_ecd     TEXT,
    abs_ecd     TEXT,
    ach_esl     TEXT,
    grw_esl     TEXT,
    abs_esl     TEXT,
    ach_asian   TEXT,
    grw_asian   TEXT,
    abs_asian   TEXT,
    ach_black   TEXT,
    grw_black   TEXT,
    abs_black   TEXT,
    ach_hsp     TEXT,
    grw_hsp     TEXT,
    abs_hsp     TEXT,
    ach_white   TEXT,
    grw_white   TEXT,
    abs_white   TEXT,
    ach_other   TEXT,
    grw_other   TEXT,
    abs_other   TEXT,
    coi         TEXT,
    coi_ed      TEXT,
    coi_he      TEXT,
    coi_st      TEXT,
    ppe         TEXT
);

\copy _al_sch24_raw (year_val, system_name, school_name, ncessch, countyid, ach_all, grw_all, abs_all, ach_ecd, grw_ecd, abs_ecd, ach_esl, grw_esl, abs_esl, ach_asian, grw_asian, abs_asian, ach_black, grw_black, abs_black, ach_hsp, grw_hsp, abs_hsp, ach_white, grw_white, abs_white, ach_other, grw_other, abs_other, coi, coi_ed, coi_he, coi_st, ppe) FROM 'flat_data/in/raw_data/crosswalks/generated/al_sch24_selected.csv' WITH (FORMAT csv, HEADER true)

CREATE TEMP TABLE _geo_population_raw (
    geoid10 TEXT,
    year TEXT,
    aian TEXT,
    asian TEXT,
    black TEXT,
    hisp TEXT,
    white TEXT,
    total TEXT
);

\copy _geo_population_raw FROM 'flat_data/in/raw_data/geographicPropertices/population.csv' WITH (FORMAT csv, HEADER true)

CREATE TEMP TABLE _geo_child_raw (
    geoid10 TEXT,
    year TEXT,
    state_fips TEXT,
    state_usps TEXT,
    state_name TEXT,
    county_fips TEXT,
    county_name TEXT,
    metro_fips TEXT,
    metro_name TEXT,
    metro_type TEXT,
    in100 TEXT,
    primary_ruca TEXT,
    c5_coi_nat TEXT,
    c5_coi_stt TEXT,
    c5_coi_met TEXT,
    r_coi_nat TEXT,
    r_coi_stt TEXT,
    r_coi_met TEXT,
    z_coi_nat TEXT,
    z_coi_stt TEXT,
    z_coi_met TEXT,
    c5_ed_nat TEXT,
    c5_ed_stt TEXT,
    c5_ed_met TEXT,
    r_ed_nat TEXT,
    r_ed_stt TEXT,
    r_ed_met TEXT,
    z_ed_nat TEXT,
    z_ed_stt TEXT,
    z_ed_met TEXT,
    c5_he_nat TEXT,
    c5_he_stt TEXT,
    c5_he_met TEXT,
    r_he_nat TEXT,
    r_he_stt TEXT,
    r_he_met TEXT,
    z_he_nat TEXT,
    z_he_stt TEXT,
    z_he_met TEXT,
    c5_se_nat TEXT,
    c5_se_stt TEXT,
    c5_se_met TEXT,
    r_se_nat TEXT,
    r_se_stt TEXT,
    r_se_met TEXT,
    z_se_nat TEXT,
    z_se_stt TEXT,
    z_se_met TEXT
);

\copy _geo_child_raw FROM 'flat_data/in/raw_data/geographicPropertices/child_opportunity_index.csv' WITH (FORMAT csv, HEADER true)

CREATE TEMP TABLE _geo_subdomains_raw AS
SELECT * FROM _geo_child_raw WITH NO DATA;

ALTER TABLE _geo_subdomains_raw
    DROP COLUMN c5_coi_nat,
    DROP COLUMN c5_coi_stt,
    DROP COLUMN c5_coi_met,
    DROP COLUMN r_coi_nat,
    DROP COLUMN r_coi_stt,
    DROP COLUMN r_coi_met,
    DROP COLUMN z_coi_nat,
    DROP COLUMN z_coi_stt,
    DROP COLUMN z_coi_met,
    DROP COLUMN c5_ed_nat,
    DROP COLUMN c5_ed_stt,
    DROP COLUMN c5_ed_met,
    DROP COLUMN r_ed_nat,
    DROP COLUMN r_ed_stt,
    DROP COLUMN r_ed_met,
    DROP COLUMN z_ed_nat,
    DROP COLUMN z_ed_stt,
    DROP COLUMN z_ed_met,
    DROP COLUMN c5_he_nat,
    DROP COLUMN c5_he_stt,
    DROP COLUMN c5_he_met,
    DROP COLUMN r_he_nat,
    DROP COLUMN r_he_stt,
    DROP COLUMN r_he_met,
    DROP COLUMN z_he_nat,
    DROP COLUMN z_he_stt,
    DROP COLUMN z_he_met,
    DROP COLUMN c5_se_nat,
    DROP COLUMN c5_se_stt,
    DROP COLUMN c5_se_met,
    DROP COLUMN r_se_nat,
    DROP COLUMN r_se_stt,
    DROP COLUMN r_se_met,
    DROP COLUMN z_se_nat,
    DROP COLUMN z_se_stt,
    DROP COLUMN z_se_met;

ALTER TABLE _geo_subdomains_raw
    ADD COLUMN c5_ed_ec_nat TEXT,
    ADD COLUMN c5_ed_ec_stt TEXT,
    ADD COLUMN c5_ed_ec_met TEXT,
    ADD COLUMN r_ed_ec_nat TEXT,
    ADD COLUMN r_ed_ec_stt TEXT,
    ADD COLUMN r_ed_ec_met TEXT,
    ADD COLUMN z_ed_ec_nat TEXT,
    ADD COLUMN z_ed_ec_stt TEXT,
    ADD COLUMN z_ed_ec_met TEXT,
    ADD COLUMN c5_ed_el_nat TEXT,
    ADD COLUMN c5_ed_el_stt TEXT,
    ADD COLUMN c5_ed_el_met TEXT,
    ADD COLUMN r_ed_el_nat TEXT,
    ADD COLUMN r_ed_el_stt TEXT,
    ADD COLUMN r_ed_el_met TEXT,
    ADD COLUMN z_ed_el_nat TEXT,
    ADD COLUMN z_ed_el_stt TEXT,
    ADD COLUMN z_ed_el_met TEXT,
    ADD COLUMN c5_ed_er_nat TEXT,
    ADD COLUMN c5_ed_er_stt TEXT,
    ADD COLUMN c5_ed_er_met TEXT,
    ADD COLUMN r_ed_er_nat TEXT,
    ADD COLUMN r_ed_er_stt TEXT,
    ADD COLUMN r_ed_er_met TEXT,
    ADD COLUMN z_ed_er_nat TEXT,
    ADD COLUMN z_ed_er_stt TEXT,
    ADD COLUMN z_ed_er_met TEXT,
    ADD COLUMN c5_ed_sp_nat TEXT,
    ADD COLUMN c5_ed_sp_stt TEXT,
    ADD COLUMN c5_ed_sp_met TEXT,
    ADD COLUMN r_ed_sp_nat TEXT,
    ADD COLUMN r_ed_sp_stt TEXT,
    ADD COLUMN r_ed_sp_met TEXT,
    ADD COLUMN z_ed_sp_nat TEXT,
    ADD COLUMN z_ed_sp_stt TEXT,
    ADD COLUMN z_ed_sp_met TEXT,
    ADD COLUMN c5_he_ep_nat TEXT,
    ADD COLUMN c5_he_ep_stt TEXT,
    ADD COLUMN c5_he_ep_met TEXT,
    ADD COLUMN r_he_ep_nat TEXT,
    ADD COLUMN r_he_ep_stt TEXT,
    ADD COLUMN r_he_ep_met TEXT,
    ADD COLUMN z_he_ep_nat TEXT,
    ADD COLUMN z_he_ep_stt TEXT,
    ADD COLUMN z_he_ep_met TEXT,
    ADD COLUMN c5_he_hr_nat TEXT,
    ADD COLUMN c5_he_hr_stt TEXT,
    ADD COLUMN c5_he_hr_met TEXT,
    ADD COLUMN r_he_hr_nat TEXT,
    ADD COLUMN r_he_hr_stt TEXT,
    ADD COLUMN r_he_hr_met TEXT,
    ADD COLUMN z_he_hr_nat TEXT,
    ADD COLUMN z_he_hr_stt TEXT,
    ADD COLUMN z_he_hr_met TEXT,
    ADD COLUMN c5_he_se_nat TEXT,
    ADD COLUMN c5_he_se_stt TEXT,
    ADD COLUMN c5_he_se_met TEXT,
    ADD COLUMN r_he_se_nat TEXT,
    ADD COLUMN r_he_se_stt TEXT,
    ADD COLUMN r_he_se_met TEXT,
    ADD COLUMN z_he_se_nat TEXT,
    ADD COLUMN z_he_se_stt TEXT,
    ADD COLUMN z_he_se_met TEXT,
    ADD COLUMN c5_he_he_nat TEXT,
    ADD COLUMN c5_he_he_stt TEXT,
    ADD COLUMN c5_he_he_met TEXT,
    ADD COLUMN r_he_he_nat TEXT,
    ADD COLUMN r_he_he_stt TEXT,
    ADD COLUMN r_he_he_met TEXT,
    ADD COLUMN z_he_he_nat TEXT,
    ADD COLUMN z_he_he_stt TEXT,
    ADD COLUMN z_he_he_met TEXT,
    ADD COLUMN c5_se_ei_nat TEXT,
    ADD COLUMN c5_se_ei_stt TEXT,
    ADD COLUMN c5_se_ei_met TEXT,
    ADD COLUMN r_se_ei_nat TEXT,
    ADD COLUMN r_se_ei_stt TEXT,
    ADD COLUMN r_se_ei_met TEXT,
    ADD COLUMN z_se_ei_nat TEXT,
    ADD COLUMN z_se_ei_stt TEXT,
    ADD COLUMN z_se_ei_met TEXT,
    ADD COLUMN c5_se_eo_nat TEXT,
    ADD COLUMN c5_se_eo_stt TEXT,
    ADD COLUMN c5_se_eo_met TEXT,
    ADD COLUMN r_se_eo_nat TEXT,
    ADD COLUMN r_se_eo_stt TEXT,
    ADD COLUMN r_se_eo_met TEXT,
    ADD COLUMN z_se_eo_nat TEXT,
    ADD COLUMN z_se_eo_stt TEXT,
    ADD COLUMN z_se_eo_met TEXT,
    ADD COLUMN c5_se_er_nat TEXT,
    ADD COLUMN c5_se_er_stt TEXT,
    ADD COLUMN c5_se_er_met TEXT,
    ADD COLUMN r_se_er_nat TEXT,
    ADD COLUMN r_se_er_stt TEXT,
    ADD COLUMN r_se_er_met TEXT,
    ADD COLUMN z_se_er_nat TEXT,
    ADD COLUMN z_se_er_stt TEXT,
    ADD COLUMN z_se_er_met TEXT,
    ADD COLUMN c5_se_hq_nat TEXT,
    ADD COLUMN c5_se_hq_stt TEXT,
    ADD COLUMN c5_se_hq_met TEXT,
    ADD COLUMN r_se_hq_nat TEXT,
    ADD COLUMN r_se_hq_stt TEXT,
    ADD COLUMN r_se_hq_met TEXT,
    ADD COLUMN z_se_hq_nat TEXT,
    ADD COLUMN z_se_hq_stt TEXT,
    ADD COLUMN z_se_hq_met TEXT,
    ADD COLUMN c5_se_sr_nat TEXT,
    ADD COLUMN c5_se_sr_stt TEXT,
    ADD COLUMN c5_se_sr_met TEXT,
    ADD COLUMN r_se_sr_nat TEXT,
    ADD COLUMN r_se_sr_stt TEXT,
    ADD COLUMN r_se_sr_met TEXT,
    ADD COLUMN z_se_sr_nat TEXT,
    ADD COLUMN z_se_sr_stt TEXT,
    ADD COLUMN z_se_sr_met TEXT,
    ADD COLUMN c5_se_wl_nat TEXT,
    ADD COLUMN c5_se_wl_stt TEXT,
    ADD COLUMN c5_se_wl_met TEXT,
    ADD COLUMN r_se_wl_nat TEXT,
    ADD COLUMN r_se_wl_stt TEXT,
    ADD COLUMN r_se_wl_met TEXT,
    ADD COLUMN z_se_wl_nat TEXT,
    ADD COLUMN z_se_wl_stt TEXT,
    ADD COLUMN z_se_wl_met TEXT;

\copy _geo_subdomains_raw FROM 'flat_data/in/raw_data/geographicPropertices/subdomains_usa.csv' WITH (FORMAT csv, HEADER true)

INSERT INTO sandbox.ref_al_district_to_county_review (
    nces_admin_id,
    county_fips,
    county_name
)
SELECT DISTINCT
    (lpad(trim(r.state_fips), 2, '0') || lpad(trim(r.district_id_number), 5, '0'))::char(7) AS nces_admin_id,
    (lpad(trim(r.state_fips), 2, '0') || lpad(trim(r.county_fips), 3, '0'))::char(5) AS county_fips,
    trim(r.county_names) AS county_name
FROM _district_to_county_raw r
WHERE upper(trim(coalesce(r.state_postal_code, ''))) = 'AL'
  AND trim(coalesce(r.state_fips, '')) ~ '^[0-9]{1,2}$'
  AND trim(coalesce(r.district_id_number, '')) ~ '^[0-9]{1,5}$'
  AND trim(coalesce(r.county_fips, '')) ~ '^[0-9]{1,3}$';

INSERT INTO sandbox.ref_school_identity_crosswalk_review (
    school_name,
    system_name,
    ncessch,
    match_method,
    priority,
    school_name_normalized,
    system_name_normalized
)
SELECT DISTINCT
    trim(r.school_name) AS school_name,
    NULLIF(trim(r.system_name), '') AS system_name,
    lpad(trim(r.ncessch), 12, '0')::char(12) AS ncessch,
    trim(r.match_method) AS match_method,
    trim(r.priority)::int AS priority,
    lower(regexp_replace(trim(r.school_name), '[[:space:]]+', ' ', 'g')) AS school_name_normalized,
    coalesce(NULLIF(lower(regexp_replace(trim(r.system_name), '[[:space:]]+', ' ', 'g')), ''), '') AS system_name_normalized
FROM _school_identity_crosswalk_raw r
WHERE trim(coalesce(r.school_name, '')) <> ''
  AND trim(coalesce(r.ncessch, '')) ~ '^[0-9]{1,12}$'
  AND trim(coalesce(r.priority, '')) ~ '^[0-9]+$';

WITH geo_src AS (
    SELECT
        g.geoid10,
        g.state_fips,
        g.state_usps,
        g.state_name,
        g.county_fips,
        g.county_name,
        g.metro_fips,
        g.metro_name,
        g.metro_type,
        g.in100,
        g.primary_ruca
    FROM _geo_child_raw g
    WHERE upper(trim(coalesce(g.state_usps, ''))) = 'AL'
      AND trim(coalesce(g.geoid10, '')) ~ '^[0-9]{11}$'

    UNION ALL

    SELECT
        g.geoid10,
        g.state_fips,
        g.state_usps,
        g.state_name,
        g.county_fips,
        g.county_name,
        g.metro_fips,
        g.metro_name,
        g.metro_type,
        g.in100,
        g.primary_ruca
    FROM _geo_subdomains_raw g
    WHERE upper(trim(coalesce(g.state_usps, ''))) = 'AL'
      AND trim(coalesce(g.geoid10, '')) ~ '^[0-9]{11}$'
),
geo_ranked AS (
    SELECT
        g.*,
        ROW_NUMBER() OVER (
            PARTITION BY g.geoid10
            ORDER BY g.geoid10
        ) AS rn
    FROM geo_src g
),
geo_meta AS (
    SELECT
        geoid10,
        NULLIF(trim(state_fips), '') AS state_fips,
        NULLIF(trim(state_usps), '') AS state_usps,
        NULLIF(trim(state_name), '') AS state_name,
        NULLIF(trim(county_fips), '') AS county_fips,
        NULLIF(trim(regexp_replace(county_name, ',[[:space:]]*Alabama$', '', 'i')), '') AS county_name,
        NULLIF(trim(metro_fips), '') AS metro_fips,
        NULLIF(trim(metro_name), '') AS metro_name,
        NULLIF(trim(metro_type), '') AS metro_type,
        CASE
            WHEN trim(coalesce(in100, '')) ~ '^[-]?[0-9]+(\.[0-9]+)?$'
                THEN trim(in100)::numeric(8,2)::smallint
            ELSE NULL
        END AS in100,
        CASE
            WHEN trim(coalesce(primary_ruca, '')) ~ '^[-]?[0-9]+(\.[0-9]+)?$'
                THEN trim(primary_ruca)::numeric(8,2)::smallint
            ELSE NULL
        END AS primary_ruca
    FROM geo_ranked
    WHERE rn = 1
),
tract_keys AS (
    SELECT DISTINCT p.geoid10
    FROM _geo_population_raw p
    WHERE trim(coalesce(p.geoid10, '')) ~ '^[0-9]{11}$'
      AND p.geoid10 LIKE '01%'

    UNION

    SELECT geoid10 FROM geo_meta
)
INSERT INTO sandbox.dim_geo_tract_review (
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
    primary_ruca
)
SELECT
    tk.geoid10::char(11) AS geoid10,
    coalesce(gm.state_fips, substring(tk.geoid10 from 1 for 2))::char(2) AS state_fips,
    coalesce(gm.state_usps, 'AL')::char(2) AS state_usps,
    coalesce(gm.state_name, 'Alabama') AS state_name,
    coalesce(gm.county_fips, substring(tk.geoid10 from 1 for 5))::char(5) AS county_fips,
    gm.county_name,
    gm.metro_fips::char(5),
    gm.metro_name,
    gm.metro_type,
    gm.in100,
    gm.primary_ruca
FROM tract_keys tk
LEFT JOIN geo_meta gm
  ON gm.geoid10 = tk.geoid10;


WITH src AS (
    SELECT
        p.geoid10::char(11) AS geoid10,
        p.year::smallint AS year,
        v.population_group,
        CASE
            WHEN upper(trim(coalesce(v.raw_value, ''))) IN ('', 'NA', 'NRD') THEN NULL
            WHEN regexp_replace(trim(v.raw_value), '[,$ ]', '', 'g') ~ '^[-]?[0-9]+(\.[0-9]+)?$'
                THEN regexp_replace(trim(v.raw_value), '[,$ ]', '', 'g')::double precision
            ELSE NULL
        END AS population_count,
        ROW_NUMBER() OVER (
            PARTITION BY p.geoid10::char(11), p.year::smallint, v.population_group
            ORDER BY p.geoid10, p.year
        ) AS rn
    FROM _geo_population_raw p
    CROSS JOIN LATERAL (
        VALUES
          ('aian', p.aian),
          ('asian', p.asian),
          ('black', p.black),
          ('hisp', p.hisp),
          ('white', p.white),
          ('total', p.total)
    ) v(population_group, raw_value)
    WHERE trim(coalesce(p.geoid10, '')) ~ '^[0-9]{11}$'
      AND p.geoid10 LIKE '01%'
      AND trim(coalesce(p.year, '')) ~ '^[0-9]{4}$'
)
INSERT INTO sandbox.fact_geo_population_review (
    geoid10,
    year,
    population_group,
    population_count
)
SELECT
    s.geoid10,
    s.year,
    s.population_group,
    s.population_count
FROM src s
JOIN sandbox.dim_geo_tract_review t
  ON t.geoid10 = s.geoid10
WHERE s.rn = 1;

WITH child_src AS (
    SELECT
        c.geoid10::char(11) AS geoid10,
        c.year::smallint AS year,
        v.metric_code,
        v.norm_scope,
        v.level_raw,
        v.score_raw,
        v.zscore_raw
    FROM _geo_child_raw c
    CROSS JOIN LATERAL (
        VALUES
          ('COI', 'nat', c.c5_coi_nat, c.r_coi_nat, c.z_coi_nat),
          ('COI', 'stt', c.c5_coi_stt, c.r_coi_stt, c.z_coi_stt),
          ('COI', 'met', c.c5_coi_met, c.r_coi_met, c.z_coi_met),
          ('ED',  'nat', c.c5_ed_nat,  c.r_ed_nat,  c.z_ed_nat),
          ('ED',  'stt', c.c5_ed_stt,  c.r_ed_stt,  c.z_ed_stt),
          ('ED',  'met', c.c5_ed_met,  c.r_ed_met,  c.z_ed_met),
          ('HE',  'nat', c.c5_he_nat,  c.r_he_nat,  c.z_he_nat),
          ('HE',  'stt', c.c5_he_stt,  c.r_he_stt,  c.z_he_stt),
          ('HE',  'met', c.c5_he_met,  c.r_he_met,  c.z_he_met),
          ('SE',  'nat', c.c5_se_nat,  c.r_se_nat,  c.z_se_nat),
          ('SE',  'stt', c.c5_se_stt,  c.r_se_stt,  c.z_se_stt),
          ('SE',  'met', c.c5_se_met,  c.r_se_met,  c.z_se_met)
    ) v(metric_code, norm_scope, level_raw, score_raw, zscore_raw)
    WHERE trim(coalesce(c.geoid10, '')) ~ '^[0-9]{11}$'
      AND trim(coalesce(c.year, '')) ~ '^[0-9]{4}$'
      AND upper(trim(coalesce(c.state_usps, ''))) = 'AL'
),
subdomain_src AS (
    SELECT
        s.geoid10::char(11) AS geoid10,
        s.year::smallint AS year,
        v.metric_code,
        v.norm_scope,
        v.level_raw,
        v.score_raw,
        v.zscore_raw
    FROM _geo_subdomains_raw s
    CROSS JOIN LATERAL (
        VALUES
          ('ED_EC', 'nat', s.c5_ed_ec_nat, s.r_ed_ec_nat, s.z_ed_ec_nat),
          ('ED_EC', 'stt', s.c5_ed_ec_stt, s.r_ed_ec_stt, s.z_ed_ec_stt),
          ('ED_EC', 'met', s.c5_ed_ec_met, s.r_ed_ec_met, s.z_ed_ec_met),
          ('ED_EL', 'nat', s.c5_ed_el_nat, s.r_ed_el_nat, s.z_ed_el_nat),
          ('ED_EL', 'stt', s.c5_ed_el_stt, s.r_ed_el_stt, s.z_ed_el_stt),
          ('ED_EL', 'met', s.c5_ed_el_met, s.r_ed_el_met, s.z_ed_el_met),
          ('ED_ER', 'nat', s.c5_ed_er_nat, s.r_ed_er_nat, s.z_ed_er_nat),
          ('ED_ER', 'stt', s.c5_ed_er_stt, s.r_ed_er_stt, s.z_ed_er_stt),
          ('ED_ER', 'met', s.c5_ed_er_met, s.r_ed_er_met, s.z_ed_er_met),
          ('ED_SP', 'nat', s.c5_ed_sp_nat, s.r_ed_sp_nat, s.z_ed_sp_nat),
          ('ED_SP', 'stt', s.c5_ed_sp_stt, s.r_ed_sp_stt, s.z_ed_sp_stt),
          ('ED_SP', 'met', s.c5_ed_sp_met, s.r_ed_sp_met, s.z_ed_sp_met),
          ('HE_EP', 'nat', s.c5_he_ep_nat, s.r_he_ep_nat, s.z_he_ep_nat),
          ('HE_EP', 'stt', s.c5_he_ep_stt, s.r_he_ep_stt, s.z_he_ep_stt),
          ('HE_EP', 'met', s.c5_he_ep_met, s.r_he_ep_met, s.z_he_ep_met),
          ('HE_HR', 'nat', s.c5_he_hr_nat, s.r_he_hr_nat, s.z_he_hr_nat),
          ('HE_HR', 'stt', s.c5_he_hr_stt, s.r_he_hr_stt, s.z_he_hr_stt),
          ('HE_HR', 'met', s.c5_he_hr_met, s.r_he_hr_met, s.z_he_hr_met),
          ('HE_SE', 'nat', s.c5_he_se_nat, s.r_he_se_nat, s.z_he_se_nat),
          ('HE_SE', 'stt', s.c5_he_se_stt, s.r_he_se_stt, s.z_he_se_stt),
          ('HE_SE', 'met', s.c5_he_se_met, s.r_he_se_met, s.z_he_se_met),
          ('HE_HE', 'nat', s.c5_he_he_nat, s.r_he_he_nat, s.z_he_he_nat),
          ('HE_HE', 'stt', s.c5_he_he_stt, s.r_he_he_stt, s.z_he_he_stt),
          ('HE_HE', 'met', s.c5_he_he_met, s.r_he_he_met, s.z_he_he_met),
          ('SE_EI', 'nat', s.c5_se_ei_nat, s.r_se_ei_nat, s.z_se_ei_nat),
          ('SE_EI', 'stt', s.c5_se_ei_stt, s.r_se_ei_stt, s.z_se_ei_stt),
          ('SE_EI', 'met', s.c5_se_ei_met, s.r_se_ei_met, s.z_se_ei_met),
          ('SE_EO', 'nat', s.c5_se_eo_nat, s.r_se_eo_nat, s.z_se_eo_nat),
          ('SE_EO', 'stt', s.c5_se_eo_stt, s.r_se_eo_stt, s.z_se_eo_stt),
          ('SE_EO', 'met', s.c5_se_eo_met, s.r_se_eo_met, s.z_se_eo_met),
          ('SE_ER', 'nat', s.c5_se_er_nat, s.r_se_er_nat, s.z_se_er_nat),
          ('SE_ER', 'stt', s.c5_se_er_stt, s.r_se_er_stt, s.z_se_er_stt),
          ('SE_ER', 'met', s.c5_se_er_met, s.r_se_er_met, s.z_se_er_met),
          ('SE_HQ', 'nat', s.c5_se_hq_nat, s.r_se_hq_nat, s.z_se_hq_nat),
          ('SE_HQ', 'stt', s.c5_se_hq_stt, s.r_se_hq_stt, s.z_se_hq_stt),
          ('SE_HQ', 'met', s.c5_se_hq_met, s.r_se_hq_met, s.z_se_hq_met),
          ('SE_SR', 'nat', s.c5_se_sr_nat, s.r_se_sr_nat, s.z_se_sr_nat),
          ('SE_SR', 'stt', s.c5_se_sr_stt, s.r_se_sr_stt, s.z_se_sr_stt),
          ('SE_SR', 'met', s.c5_se_sr_met, s.r_se_sr_met, s.z_se_sr_met),
          ('SE_WL', 'nat', s.c5_se_wl_nat, s.r_se_wl_nat, s.z_se_wl_nat),
          ('SE_WL', 'stt', s.c5_se_wl_stt, s.r_se_wl_stt, s.z_se_wl_stt),
          ('SE_WL', 'met', s.c5_se_wl_met, s.r_se_wl_met, s.z_se_wl_met)
    ) v(metric_code, norm_scope, level_raw, score_raw, zscore_raw)
    WHERE trim(coalesce(s.geoid10, '')) ~ '^[0-9]{11}$'
      AND trim(coalesce(s.year, '')) ~ '^[0-9]{4}$'
      AND upper(trim(coalesce(s.state_usps, ''))) = 'AL'
),
typed AS (
    SELECT
        x.geoid10,
        x.year,
        x.metric_code,
        x.norm_scope,
        CASE lower(trim(coalesce(x.level_raw, '')))
            WHEN 'very low' THEN 'Very Low'
            WHEN 'low' THEN 'Low'
            WHEN 'moderate' THEN 'Moderate'
            WHEN 'high' THEN 'High'
            WHEN 'very high' THEN 'Very High'
            ELSE NULL
        END AS opportunity_level,
        CASE
            WHEN upper(trim(coalesce(x.score_raw, ''))) IN ('', 'NA', 'NRD') THEN NULL
            WHEN regexp_replace(trim(x.score_raw), '[,$ ]', '', 'g') ~ '^[-]?[0-9]+(\.[0-9]+)?$'
                THEN regexp_replace(trim(x.score_raw), '[,$ ]', '', 'g')::numeric(8,4)::smallint
            ELSE NULL
        END AS opportunity_score,
        CASE
            WHEN upper(trim(coalesce(x.zscore_raw, ''))) IN ('', 'NA', 'NRD') THEN NULL
            WHEN regexp_replace(trim(x.zscore_raw), '[,$ ]', '', 'g') ~ '^[-]?[0-9]+(\.[0-9]+)?$'
                THEN regexp_replace(trim(x.zscore_raw), '[,$ ]', '', 'g')::double precision
            ELSE NULL
        END AS opportunity_zscore
    FROM (
        SELECT * FROM child_src
        UNION ALL
        SELECT * FROM subdomain_src
    ) x
),
ranked AS (
    SELECT
        t.*,
        ROW_NUMBER() OVER (
            PARTITION BY t.geoid10, t.year, t.metric_code, t.norm_scope
            ORDER BY t.geoid10, t.year, t.metric_code, t.norm_scope
        ) AS rn
    FROM typed t
)
INSERT INTO sandbox.fact_geo_opportunity_review (
    geoid10,
    year,
    metric_code,
    norm_scope,
    opportunity_level,
    opportunity_score,
    opportunity_zscore
)
SELECT
    r.geoid10,
    r.year,
    r.metric_code,
    r.norm_scope,
    r.opportunity_level,
    r.opportunity_score,
    r.opportunity_zscore
FROM ranked r
JOIN sandbox.dim_geo_tract_review t
  ON t.geoid10 = r.geoid10
WHERE r.rn = 1
  AND (
      r.opportunity_level IS NOT NULL
      OR r.opportunity_score IS NOT NULL
      OR r.opportunity_zscore IS NOT NULL
  );


WITH typed AS (
    SELECT
        CASE
            WHEN trim(coalesce(r.year_val, '')) ~ '^[0-9]{4}$' THEN trim(r.year_val)::smallint
            ELSE NULL
        END AS year,
        trim(regexp_replace(r.system_name, '[[:space:]]+', ' ', 'g')) AS dist_name,
        trim(regexp_replace(r.school_name, '[[:space:]]+', ' ', 'g')) AS school_name,
        CASE
            WHEN trim(coalesce(r.ncessch, '')) ~ '^[0-9]+$' THEN lpad(trim(r.ncessch), 12, '0')::char(12)
            ELSE NULL
        END AS ncessch,
        CASE
            WHEN trim(coalesce(r.countyid, '')) ~ '^[0-9]+$' THEN lpad(trim(r.countyid), 5, '0')::char(5)
            ELSE NULL
        END AS county_fips,
        CASE
            WHEN trim(coalesce(r.ach_all, '')) ~ '^[-]?[0-9]+(\.[0-9]+)?$' THEN trim(r.ach_all)::double precision
            ELSE NULL
        END AS ach_all,
        CASE
            WHEN trim(coalesce(r.grw_all, '')) ~ '^[-]?[0-9]+(\.[0-9]+)?$' THEN trim(r.grw_all)::double precision
            ELSE NULL
        END AS grw_all,
        CASE
            WHEN trim(coalesce(r.abs_all, '')) ~ '^[-]?[0-9]+(\.[0-9]+)?$' THEN trim(r.abs_all)::double precision
            ELSE NULL
        END AS abs_all,
        CASE
            WHEN trim(coalesce(r.coi, '')) ~ '^[-]?[0-9]+(\.[0-9]+)?$' THEN trim(r.coi)::double precision
            ELSE NULL
        END AS coi,
        CASE
            WHEN trim(coalesce(r.coi_ed, '')) ~ '^[-]?[0-9]+(\.[0-9]+)?$' THEN trim(r.coi_ed)::double precision
            ELSE NULL
        END AS coi_ed,
        CASE
            WHEN trim(coalesce(r.coi_he, '')) ~ '^[-]?[0-9]+(\.[0-9]+)?$' THEN trim(r.coi_he)::double precision
            ELSE NULL
        END AS coi_he,
        CASE
            WHEN trim(coalesce(r.coi_st, '')) ~ '^[-]?[0-9]+(\.[0-9]+)?$' THEN trim(r.coi_st)::double precision
            ELSE NULL
        END AS coi_st,
        CASE
            WHEN trim(coalesce(r.ppe, '')) ~ '^[-]?[0-9]+(\.[0-9]+)?$' THEN trim(r.ppe)::double precision
            ELSE NULL
        END AS ppe
    FROM _al_sch24_raw r
),
ranked AS (
    SELECT
        t.*,
        ROW_NUMBER() OVER (
            PARTITION BY t.year, lower(t.dist_name), lower(t.school_name)
            ORDER BY
                CASE WHEN t.ach_all IS NOT NULL THEN 1 ELSE 0 END DESC,
                CASE WHEN t.grw_all IS NOT NULL THEN 1 ELSE 0 END DESC,
                CASE WHEN t.abs_all IS NOT NULL THEN 1 ELSE 0 END DESC
        ) AS rn
    FROM typed t
    WHERE t.year IS NOT NULL
      AND t.dist_name IS NOT NULL
      AND t.school_name IS NOT NULL
)
INSERT INTO sandbox.fact_school_outcomes_wide_review (
    year,
    dist_name,
    school_name,
    ncessch,
    county_fips,
    ach_all,
    grw_all,
    abs_all,
    coi,
    coi_ed,
    coi_he,
    coi_st,
    ppe
)
SELECT
    r.year,
    r.dist_name,
    r.school_name,
    r.ncessch,
    r.county_fips,
    r.ach_all,
    r.grw_all,
    r.abs_all,
    r.coi,
    r.coi_ed,
    r.coi_he,
    r.coi_st,
    r.ppe
FROM ranked r
WHERE r.rn = 1;

WITH year_bounds AS (
    SELECT
        min(year) AS min_year,
        max(year) AS max_year
    FROM sandbox.fact_geo_opportunity_review
),
school_base AS (
    SELECT
        s.school_key,
        s.school_year_start,
        s.dist_name,
        s.school_name,
        lpad(s.nces_admin_id::text, 7, '0') AS nces_admin_id,
        lower(regexp_replace(trim(s.school_name), '[[:space:]]+', ' ', 'g')) AS school_name_norm,
        lower(regexp_replace(trim(s.dist_name), '[[:space:]]+', ' ', 'g')) AS dist_name_norm
    FROM sandbox.dim_school_info_review_v2 s
),
county_base AS (
    SELECT
        t.county_fips,
        max(t.county_name) FILTER (WHERE nullif(trim(t.county_name), '') IS NOT NULL) AS county_name,
        lower(regexp_replace(trim(coalesce(
            max(t.county_name) FILTER (WHERE nullif(trim(t.county_name), '') IS NOT NULL),
            t.county_fips::text
        )), '[[:space:]]+', ' ', 'g')) AS county_name_normalized
    FROM sandbox.dim_geo_tract_review t
    GROUP BY t.county_fips
),
district_county_map AS (
    SELECT
        m.nces_admin_id,
        count(*)::int AS county_count,
        min(m.county_fips) AS county_fips,
        min(m.county_name) AS county_name
    FROM sandbox.ref_al_district_to_county_review m
    GROUP BY m.nces_admin_id
),
crosswalk_ranked AS (
    SELECT
        c.school_name_normalized,
        c.system_name_normalized,
        c.ncessch,
        c.match_method,
        c.priority,
        max(c.priority) OVER (
            PARTITION BY c.school_name_normalized, c.system_name_normalized
        ) AS top_priority
    FROM sandbox.ref_school_identity_crosswalk_review c
),
crosswalk_best AS (
    SELECT
        c.school_name_normalized,
        c.system_name_normalized,
        min(c.ncessch) AS ncessch,
        min(c.match_method) AS match_method,
        count(DISTINCT c.ncessch)::int AS ncessch_count
    FROM crosswalk_ranked c
    WHERE c.priority = c.top_priority
    GROUP BY c.school_name_normalized, c.system_name_normalized
),
school_county_year AS (
    SELECT
        lpad(trim(r.ncessch), 12, '0')::char(12) AS ncessch,
        trim(r.year_val)::smallint AS year,
        count(DISTINCT lpad(trim(r.countyid), 5, '0'))::int AS county_count,
        min(lpad(trim(r.countyid), 5, '0'))::char(5) AS county_fips
    FROM _al_sch24_raw r
    WHERE trim(coalesce(r.ncessch, '')) ~ '^[0-9]+$'
      AND trim(coalesce(r.year_val, '')) ~ '^[0-9]{4}$'
      AND trim(coalesce(r.countyid, '')) ~ '^[0-9]+$'
    GROUP BY lpad(trim(r.ncessch), 12, '0'), trim(r.year_val)::smallint
)
INSERT INTO sandbox.bridge_school_geo_county_review (
    school_key,
    school_year_start,
    dist_name,
    county_fips,
    county_name,
    match_method,
    match_confidence,
    strict_null_reason
)
SELECT
    s.school_key,
    s.school_year_start,
    s.dist_name,
    CASE
        WHEN s.school_year_start < y.min_year OR s.school_year_start > y.max_year THEN NULL
        WHEN sc.county_count = 1 THEN sc.county_fips
        WHEN c.county_fips IS NOT NULL THEN c.county_fips
        WHEN d.county_count = 1 THEN d.county_fips
        ELSE NULL
    END AS county_fips,
    CASE
        WHEN s.school_year_start < y.min_year OR s.school_year_start > y.max_year THEN NULL
        WHEN sc.county_count = 1 THEN gc.county_name
        WHEN c.county_fips IS NOT NULL THEN c.county_name
        WHEN d.county_count = 1 THEN d.county_name
        ELSE NULL
    END AS county_name,
    CASE
        WHEN s.school_year_start < y.min_year OR s.school_year_start > y.max_year THEN NULL
        WHEN sc.county_count = 1 AND xb.match_method = 'HAND_MATCH' THEN 'hand_match_ncessch'
        WHEN sc.county_count = 1 THEN 'ncessch_crosswalk'
        WHEN c.county_fips IS NOT NULL THEN 'dist_name_exact_county'
        WHEN d.county_count = 1 THEN 'nces_admin_crosswalk'
        ELSE NULL
    END AS match_method,
    CASE
        WHEN s.school_year_start < y.min_year OR s.school_year_start > y.max_year THEN NULL
        WHEN sc.county_count = 1 THEN 1.000::numeric(4,3)
        WHEN c.county_fips IS NOT NULL THEN 1.000::numeric(4,3)
        WHEN d.county_count = 1 THEN 1.000::numeric(4,3)
        ELSE NULL
    END AS match_confidence,
    CASE
        WHEN y.min_year IS NULL OR y.max_year IS NULL THEN 'NO_GEO_YEAR_RANGE'
        WHEN s.school_year_start < y.min_year OR s.school_year_start > y.max_year THEN 'YEAR_OUT_OF_RANGE'
        WHEN xb.ncessch_count > 1 THEN 'AMBIGUOUS_NCESSCH_MATCH'
        WHEN xb.ncessch IS NOT NULL AND (sc.county_count IS NULL OR sc.county_count = 0)
            AND c.county_fips IS NULL AND (d.county_count IS NULL OR d.county_count = 0)
            THEN 'NO_NCESSCH_RESOLUTION'
        WHEN sc.county_count > 1 THEN 'AMBIGUOUS_SCHOOL_COUNTY'
        WHEN c.county_fips IS NULL AND d.county_count > 1 THEN 'AMBIGUOUS_DISTRICT_COUNTY'
        WHEN c.county_fips IS NULL AND (d.county_count IS NULL OR d.county_count = 0) THEN 'NO_EXACT_COUNTY_MATCH'
        ELSE NULL
    END AS strict_null_reason
FROM school_base s
LEFT JOIN LATERAL (
    SELECT
        b.ncessch,
        b.match_method,
        b.ncessch_count
    FROM crosswalk_best b
    WHERE b.school_name_normalized = s.school_name_norm
      AND (
          b.system_name_normalized = s.dist_name_norm
          OR b.system_name_normalized = ''
      )
    ORDER BY
        CASE WHEN b.system_name_normalized = s.dist_name_norm THEN 0 ELSE 1 END,
        b.ncessch
    LIMIT 1
) xb ON TRUE
LEFT JOIN school_county_year sc
  ON sc.ncessch = xb.ncessch
 AND sc.year = s.school_year_start
LEFT JOIN county_base gc
  ON gc.county_fips = sc.county_fips
LEFT JOIN county_base c
  ON c.county_name_normalized = s.dist_name_norm
LEFT JOIN district_county_map d
  ON d.nces_admin_id = s.nces_admin_id
CROSS JOIN year_bounds y;

CREATE INDEX idx_dim_geo_tract_review_county
  ON sandbox.dim_geo_tract_review (county_fips);
CREATE INDEX idx_fact_geo_population_review_year
  ON sandbox.fact_geo_population_review (year, population_group);
CREATE INDEX idx_fact_geo_opportunity_review_year
  ON sandbox.fact_geo_opportunity_review (year, metric_code, norm_scope);
CREATE INDEX idx_bridge_school_geo_county_review_reason
  ON sandbox.bridge_school_geo_county_review (school_year_start, strict_null_reason);
CREATE INDEX idx_ref_al_district_to_county_review_county
  ON sandbox.ref_al_district_to_county_review (county_fips);
CREATE INDEX idx_ref_school_identity_crosswalk_review_norm
  ON sandbox.ref_school_identity_crosswalk_review (school_name_normalized, system_name_normalized, priority);
CREATE INDEX idx_fact_school_outcomes_wide_review_year
  ON sandbox.fact_school_outcomes_wide_review (year, dist_name, school_name);

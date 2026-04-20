CREATE TABLE IF NOT EXISTS gold.dim_state (
    state_key BIGINT PRIMARY KEY,
    state_code CHAR(2) NOT NULL UNIQUE,
    department_name TEXT NOT NULL,
    _created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS gold.dim_district (
    district_key BIGINT PRIMARY KEY,
    state_key BIGINT NOT NULL REFERENCES gold.dim_state(state_key),
    district_name TEXT NOT NULL,
    district_name_norm TEXT NOT NULL,
    state_code CHAR(2) NOT NULL,
    state_dist_id INTEGER,
    nces_admin_id BIGINT,
    source_state_dist_id TEXT,
    _created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_gold_dim_district UNIQUE (state_code, district_name_norm)
);

CREATE TABLE IF NOT EXISTS gold.dim_school (
    school_key BIGINT PRIMARY KEY,
    district_key BIGINT NOT NULL REFERENCES gold.dim_district(district_key),
    school_name TEXT NOT NULL,
    school_name_norm TEXT NOT NULL,
    state_code CHAR(2) NOT NULL,
    state_school_id INTEGER,
    nces_geo_id BIGINT,
    census_id BIGINT,
    nces_id BIGINT,
    nces_charter BOOLEAN,
    nces_magnet BOOLEAN,
    nces_address TEXT,
    nces_city VARCHAR(120),
    nces_zip VARCHAR(15),
    source_state_school_id TEXT,
    _created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_gold_dim_school UNIQUE (district_key, school_name_norm)
);

CREATE TABLE IF NOT EXISTS gold.bridge_school_year (
    school_key BIGINT NOT NULL REFERENCES gold.dim_school(school_key),
    school_year_label VARCHAR(9) NOT NULL,
    school_year_start SMALLINT NOT NULL,
    school_year_end SMALLINT,
    nces_locale_key SMALLINT NOT NULL REFERENCES ref.nces_locale_canonical(nces_locale_key),
    nces_locale_type VARCHAR(20),
    nces_locale_subtype VARCHAR(20),
    source_nces_locale TEXT,
    _source_file TEXT,
    _ingested_at TIMESTAMP,
    _created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_gold_bridge_school_year PRIMARY KEY (school_key, school_year_start)
);

CREATE TABLE IF NOT EXISTS gold.dim_school_info (
    school_key BIGINT NOT NULL,
    school_year_label VARCHAR(9) NOT NULL,
    school_year_start SMALLINT NOT NULL,
    school_year_end SMALLINT,
    state_code CHAR(2) NOT NULL,
    state_dist_id INTEGER,
    state_school_id INTEGER,
    nces_admin_id BIGINT,
    nces_geo_id BIGINT,
    census_id BIGINT,
    nces_id BIGINT,
    dist_name TEXT NOT NULL,
    school_name TEXT NOT NULL,
    nces_locale_key SMALLINT NOT NULL REFERENCES ref.nces_locale_canonical(nces_locale_key),
    nces_locale_type VARCHAR(20),
    nces_locale_subtype VARCHAR(20),
    source_nces_locale TEXT,
    nces_charter BOOLEAN,
    nces_magnet BOOLEAN,
    nces_address TEXT,
    nces_city VARCHAR(120),
    nces_zip VARCHAR(15),
    _created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_gold_dim_school_info PRIMARY KEY (school_key, school_year_start),
    CONSTRAINT uq_gold_school_bk UNIQUE (school_year_label, dist_name, school_name)
);

CREATE TABLE IF NOT EXISTS gold.fact_teacher_demographics (
    school_key BIGINT NOT NULL,
    year SMALLINT NOT NULL,
    gender TEXT NOT NULL REFERENCES ref.gender_canonical(canonical_value),
    race TEXT NOT NULL REFERENCES ref.race_canonical(canonical_value),
    ethnicity TEXT NOT NULL REFERENCES ref.ethnicity_canonical(canonical_value),
    sub_population TEXT NOT NULL REFERENCES ref.staff_position_canonical(canonical_value),
    demographic_count DOUBLE PRECISION,
    demographic_rate DOUBLE PRECISION,
    imputed_flag BOOLEAN NOT NULL DEFAULT FALSE,
    imputation_method TEXT,
    _created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_gold_teacher_long PRIMARY KEY (school_key, year, gender, race, ethnicity, sub_population),
    CONSTRAINT fk_gold_teacher_demo_school_year FOREIGN KEY (school_key, year)
      REFERENCES gold.dim_school_info(school_key, school_year_start)
);

CREATE TABLE IF NOT EXISTS gold.fact_student_demographics (
    school_key BIGINT NOT NULL,
    year SMALLINT NOT NULL,
    grade TEXT NOT NULL,
    gender TEXT NOT NULL REFERENCES ref.gender_canonical(canonical_value),
    ethnicity TEXT NOT NULL REFERENCES ref.ethnicity_canonical(canonical_value),
    race TEXT NOT NULL REFERENCES ref.race_canonical(canonical_value),
    sub_population TEXT NOT NULL,
    demographic_count DOUBLE PRECISION,
    _created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_gold_student_long PRIMARY KEY (school_key, year, grade, gender, ethnicity, race, sub_population),
    CONSTRAINT fk_gold_student_demo_school_year FOREIGN KEY (school_key, year)
      REFERENCES gold.dim_school_info(school_key, school_year_start)
);

CREATE TABLE IF NOT EXISTS gold.fact_accountability (
    school_key BIGINT NOT NULL,
    year SMALLINT NOT NULL,
    indicator TEXT NOT NULL,
    grade TEXT NOT NULL,
    gender TEXT NOT NULL REFERENCES ref.gender_canonical(canonical_value),
    race TEXT NOT NULL REFERENCES ref.race_canonical(canonical_value),
    ethnicity TEXT NOT NULL REFERENCES ref.ethnicity_canonical(canonical_value),
    sub_population TEXT NOT NULL,
    score DOUBLE PRECISION,
    _created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_gold_fact_accountability PRIMARY KEY
      (school_key, year, indicator, grade, gender, race, ethnicity, sub_population),
    CONSTRAINT fk_gold_accountability_school_year FOREIGN KEY (school_key, year)
      REFERENCES gold.dim_school_info(school_key, school_year_start)
);

CREATE TABLE IF NOT EXISTS gold.fact_edunomics (
    school_key BIGINT NOT NULL,
    year SMALLINT NOT NULL,
    ncesenroll INTEGER,
    gradespan VARCHAR(30),
    level SMALLINT,
    enroll_raw INTEGER,
    state_local_per_pupil NUMERIC(14,2),
    state_local_fund NUMERIC(16,2),
    nces_fund NUMERIC(16,2),
    nces_poverty NUMERIC(8,4),
    title_i_status TEXT,
    nces_charter BOOLEAN,
    nces_magnet BOOLEAN,
    nces_freelunch INTEGER,
    nces_reducedlunch INTEGER,
    per_pupil_nces_raw NUMERIC(14,2),
    per_pupil_total_raw NUMERIC(14,2),
    per_pupil_total_norm_nerds NUMERIC(14,2),
    per_pupil_site_stloc_raw_al INTEGER,
    per_pupil_site_nces_raw_al INTEGER,
    per_pupil_site_raw_al INTEGER,
    per_pupil_centshare_stloc_raw_al INTEGER,
    per_pupil_centshare_nces_raw_al INTEGER,
    per_pupil_centshare_raw_al INTEGER,
    flag_nerds BOOLEAN,
    flag_f33 BOOLEAN,
    _created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_gold_fact_edunomics PRIMARY KEY (school_key, year),
    CONSTRAINT fk_gold_edunomics_school_year FOREIGN KEY (school_key, year)
      REFERENCES gold.dim_school_info(school_key, school_year_start)
);

CREATE TABLE IF NOT EXISTS gold.fact_teacher_effectiveness (
    school_key BIGINT NOT NULL,
    year SMALLINT NOT NULL,
    score DOUBLE PRECISION,
    atot_completion_rate_designation TEXT,
    title_i_status TEXT,
    _created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_gold_fact_teacher_effectiveness PRIMARY KEY (school_key, year),
    CONSTRAINT fk_gold_teacher_effect_school_year FOREIGN KEY (school_key, year)
      REFERENCES gold.dim_school_info(school_key, school_year_start)
);

CREATE TABLE IF NOT EXISTS gold.fact_teacher_experience (
    school_key BIGINT NOT NULL,
    year SMALLINT NOT NULL,
    gender TEXT NOT NULL REFERENCES ref.gender_canonical(canonical_value),
    race TEXT NOT NULL REFERENCES ref.race_canonical(canonical_value),
    ethnicity TEXT NOT NULL REFERENCES ref.ethnicity_canonical(canonical_value),
    sub_population TEXT NOT NULL,
    total_count NUMERIC(14,2),
    exp_count NUMERIC(14,2),
    exp_rate NUMERIC(8,4),
    inexp_count NUMERIC(14,2),
    inexp_rate NUMERIC(8,4),
    _created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_gold_teacher_experience PRIMARY KEY
      (school_key, year, gender, race, ethnicity, sub_population),
    CONSTRAINT fk_gold_teacher_exp_school_year FOREIGN KEY (school_key, year)
      REFERENCES gold.dim_school_info(school_key, school_year_start)
);

CREATE TABLE IF NOT EXISTS gold.dim_geo_tract (
    geoid10 CHAR(11) PRIMARY KEY,
    county_fips CHAR(5),
    county_name TEXT,
    tract_name TEXT,
    state_abbr CHAR(2),
    state_fips CHAR(2),
    urbanicity TEXT
);

CREATE TABLE IF NOT EXISTS gold.fact_geo_population (
    geoid10 CHAR(11) NOT NULL REFERENCES gold.dim_geo_tract(geoid10),
    year SMALLINT NOT NULL,
    population_group TEXT NOT NULL REFERENCES ref.geo_population_group(population_group),
    population_count INTEGER,
    population_share NUMERIC(8,4),
    PRIMARY KEY (geoid10, year, population_group)
);

CREATE TABLE IF NOT EXISTS gold.fact_geo_opportunity (
    geoid10 CHAR(11) NOT NULL REFERENCES gold.dim_geo_tract(geoid10),
    year SMALLINT NOT NULL,
    metric_code TEXT NOT NULL REFERENCES ref.geo_metric(metric_code),
    norm_scope TEXT NOT NULL REFERENCES ref.geo_norm_scope(norm_scope),
    score NUMERIC(12,6),
    zscore NUMERIC(12,6),
    percentile NUMERIC(7,4),
    opportunity_level TEXT REFERENCES ref.geo_opportunity_level(canonical_value),
    PRIMARY KEY (geoid10, year, metric_code, norm_scope)
);

CREATE TABLE IF NOT EXISTS gold.fact_geo_population_county (
    county_fips CHAR(5) NOT NULL,
    year SMALLINT NOT NULL,
    population_group TEXT NOT NULL REFERENCES ref.geo_population_group(population_group),
    population_count BIGINT,
    population_share NUMERIC(8,4),
    PRIMARY KEY (county_fips, year, population_group)
);

CREATE TABLE IF NOT EXISTS gold.fact_geo_opportunity_county (
    county_fips CHAR(5) NOT NULL,
    year SMALLINT NOT NULL,
    metric_code TEXT NOT NULL REFERENCES ref.geo_metric(metric_code),
    norm_scope TEXT NOT NULL REFERENCES ref.geo_norm_scope(norm_scope),
    score_mean NUMERIC(12,6),
    score_median NUMERIC(12,6),
    percentile_mean NUMERIC(7,4),
    opportunity_level_mode TEXT REFERENCES ref.geo_opportunity_level(canonical_value),
    PRIMARY KEY (county_fips, year, metric_code, norm_scope)
);

CREATE TABLE IF NOT EXISTS gold.bridge_school_geo_county (
    school_key BIGINT NOT NULL,
    school_year_start SMALLINT NOT NULL,
    county_fips CHAR(5),
    county_name TEXT,
    match_method TEXT,
    strict_null_reason TEXT,
    PRIMARY KEY (school_key, school_year_start),
    CONSTRAINT fk_gold_school_geo_school_year FOREIGN KEY (school_key, school_year_start)
      REFERENCES gold.dim_school_info(school_key, school_year_start)
);

CREATE TABLE IF NOT EXISTS gold.fact_school_outcomes_wide (
    school_key BIGINT NOT NULL,
    year SMALLINT NOT NULL,
    enrollment INTEGER,
    ach_all DOUBLE PRECISION,
    grw_all DOUBLE PRECISION,
    abs_all DOUBLE PRECISION,
    ach_ecd DOUBLE PRECISION,
    grw_ecd DOUBLE PRECISION,
    abs_ecd DOUBLE PRECISION,
    ach_esl DOUBLE PRECISION,
    grw_esl DOUBLE PRECISION,
    abs_esl DOUBLE PRECISION,
    ach_asian DOUBLE PRECISION,
    grw_asian DOUBLE PRECISION,
    abs_asian DOUBLE PRECISION,
    ach_black DOUBLE PRECISION,
    grw_black DOUBLE PRECISION,
    abs_black DOUBLE PRECISION,
    ach_hsp DOUBLE PRECISION,
    grw_hsp DOUBLE PRECISION,
    abs_hsp DOUBLE PRECISION,
    ach_white DOUBLE PRECISION,
    grw_white DOUBLE PRECISION,
    abs_white DOUBLE PRECISION,
    ach_other DOUBLE PRECISION,
    grw_other DOUBLE PRECISION,
    abs_other DOUBLE PRECISION,
    PRIMARY KEY (school_key, year),
    CONSTRAINT fk_gold_outcomes_school_year FOREIGN KEY (school_key, year)
      REFERENCES gold.dim_school_info(school_key, school_year_start)
);

CREATE TABLE IF NOT EXISTS gold.fact_school_outcomes_demographic (
    school_key BIGINT NOT NULL,
    year SMALLINT NOT NULL,
    indicator TEXT NOT NULL,
    subgroup TEXT NOT NULL,
    score DOUBLE PRECISION,
    PRIMARY KEY (school_key, year, indicator, subgroup),
    CONSTRAINT fk_gold_outcomes_demo_school FOREIGN KEY (school_key)
      REFERENCES gold.dim_school(school_key)
);

CREATE INDEX IF NOT EXISTS idx_gold_dim_school_info_year_name
    ON gold.dim_school_info (school_year_start, dist_name, school_name);
CREATE INDEX IF NOT EXISTS idx_gold_fact_edunomics_year_school
    ON gold.fact_edunomics (year, school_key);
CREATE INDEX IF NOT EXISTS idx_gold_fact_outcomes_year_school
    ON gold.fact_school_outcomes_wide (year, school_key);
CREATE INDEX IF NOT EXISTS idx_gold_bridge_school_geo_reason
    ON gold.bridge_school_geo_county (school_year_start, strict_null_reason);

CREATE OR REPLACE VIEW gold.vw_school_year_geo_bridge AS
SELECT
    d.school_key,
    d.school_year_start,
    d.school_year_label,
    d.dist_name,
    d.school_name,
    b.county_fips,
    b.county_name,
    b.match_method,
    b.strict_null_reason
FROM gold.dim_school_info d
LEFT JOIN gold.bridge_school_geo_county b
  ON b.school_key = d.school_key
 AND b.school_year_start = d.school_year_start;

CREATE OR REPLACE VIEW gold.vw_school_year_geo_opportunity AS
SELECT
    sb.school_key,
    sb.school_year_start,
    sb.school_year_label,
    sb.dist_name,
    sb.school_name,
    go.metric_code,
    go.norm_scope,
    go.score_mean,
    go.score_median,
    go.percentile_mean,
    go.opportunity_level_mode
FROM gold.vw_school_year_geo_bridge sb
LEFT JOIN gold.fact_geo_opportunity_county go
  ON go.county_fips = sb.county_fips
 AND go.year = sb.school_year_start;

CREATE OR REPLACE VIEW gold.vw_school_year_geo_population AS
SELECT
    sb.school_key,
    sb.school_year_start,
    sb.school_year_label,
    sb.dist_name,
    sb.school_name,
    gp.population_group,
    gp.population_count,
    gp.population_share
FROM gold.vw_school_year_geo_bridge sb
LEFT JOIN gold.fact_geo_population_county gp
  ON gp.county_fips = sb.county_fips
 AND gp.year = sb.school_year_start;

CREATE OR REPLACE VIEW gold.vw_school_year_geo_context AS
SELECT
    sy.school_key,
    sy.school_year_start AS year,
    sy.school_year_label,
    d.district_name AS dist_name,
    s.school_name,
    st.state_code,
    b.county_fips,
    b.county_name,
    b.match_method,
    b.strict_null_reason
FROM gold.bridge_school_year sy
JOIN gold.dim_school s ON s.school_key = sy.school_key
JOIN gold.dim_district d ON d.district_key = s.district_key
JOIN gold.dim_state st ON st.state_key = d.state_key
LEFT JOIN gold.bridge_school_geo_county b
  ON b.school_key = sy.school_key
 AND b.school_year_start = sy.school_year_start;

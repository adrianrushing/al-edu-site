CREATE TABLE IF NOT EXISTS sandbox.impute_teacher_demographics (
    year INTEGER,
    system TEXT,
    school TEXT,
    gender TEXT,
    race TEXT,
    ethnicity TEXT,
    sub_population TEXT,
    demographic_count DOUBLE PRECISION,
    total_count DOUBLE PRECISION,
    demographic_rate DOUBLE PRECISION,
    imputed_flag BOOLEAN,
    imputation_method TEXT,
    _source_file TEXT,
    _ingested_at TIMESTAMP,
    _processed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sandbox.impute_student_demographics_long (
    year INTEGER,
    system TEXT,
    school TEXT,
    grade TEXT,
    gender TEXT,
    ethnicity TEXT,
    race TEXT,
    sub_population TEXT,
    count BIGINT
);

CREATE TABLE IF NOT EXISTS sandbox.dim_state_review (
    state_key BIGINT PRIMARY KEY,
    state_code CHAR(2) NOT NULL UNIQUE,
    department_name TEXT NOT NULL,
    _created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sandbox.dim_district_review (
    district_key BIGINT PRIMARY KEY,
    state_key BIGINT NOT NULL REFERENCES sandbox.dim_state_review(state_key),
    state_code CHAR(2) NOT NULL,
    district_name TEXT NOT NULL,
    district_name_norm TEXT NOT NULL,
    state_dist_id INTEGER,
    nces_admin_id BIGINT,
    source_state_dist_id TEXT,
    _created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_dim_district_review UNIQUE (state_code, district_name_norm)
);

CREATE TABLE IF NOT EXISTS sandbox.dim_school_review (
    school_key BIGINT PRIMARY KEY,
    district_key BIGINT NOT NULL REFERENCES sandbox.dim_district_review(district_key),
    state_code CHAR(2) NOT NULL,
    school_name TEXT NOT NULL,
    school_name_norm TEXT NOT NULL,
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
    CONSTRAINT uq_dim_school_review UNIQUE (district_key, school_name_norm)
);

CREATE TABLE IF NOT EXISTS sandbox.bridge_school_year_review (
    school_key BIGINT NOT NULL REFERENCES sandbox.dim_school_review(school_key),
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
    CONSTRAINT pk_bridge_school_year_review PRIMARY KEY (school_key, school_year_start)
);

CREATE TABLE IF NOT EXISTS sandbox.dim_school_info_review (
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
    nces_charter BOOLEAN,
    nces_magnet BOOLEAN,
    nces_address TEXT,
    nces_city VARCHAR(120),
    nces_zip VARCHAR(15),
    source_nces_locale TEXT,
    source_state_dist_id TEXT,
    source_state_school_id TEXT,
    _source_file TEXT,
    _ingested_at TIMESTAMP,
    _created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_dim_school_info_review PRIMARY KEY (school_key, school_year_start)
);

CREATE TABLE IF NOT EXISTS sandbox.fact_teacher_demographics_long_review (
    year SMALLINT NOT NULL,
    dist_name TEXT NOT NULL,
    school_name TEXT NOT NULL,
    gender TEXT NOT NULL,
    race TEXT NOT NULL,
    ethnicity TEXT NOT NULL,
    sub_population TEXT NOT NULL,
    demographic_count DOUBLE PRECISION,
    demographic_rate DOUBLE PRECISION,
    imputed_flag BOOLEAN NOT NULL DEFAULT FALSE,
    imputation_method TEXT
);

CREATE TABLE IF NOT EXISTS sandbox.fact_student_demographics_long_review (
    year SMALLINT NOT NULL,
    dist_name TEXT NOT NULL,
    school_name TEXT NOT NULL,
    grade TEXT NOT NULL,
    gender TEXT NOT NULL,
    race TEXT NOT NULL,
    ethnicity TEXT NOT NULL,
    sub_population TEXT NOT NULL,
    demographic_count DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS sandbox.fact_accountability_review (
    year SMALLINT NOT NULL,
    dist_name TEXT NOT NULL,
    school_name TEXT NOT NULL,
    indicator TEXT NOT NULL,
    grade TEXT NOT NULL,
    gender TEXT NOT NULL,
    race TEXT NOT NULL,
    ethnicity TEXT NOT NULL,
    sub_population TEXT NOT NULL,
    score DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS sandbox.fact_edunomics_review (
    school_year_label VARCHAR(9),
    year SMALLINT NOT NULL,
    dist_name TEXT NOT NULL,
    school_name TEXT NOT NULL,
    state_dist_id INTEGER,
    state_school_id INTEGER,
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
    flag_f33 BOOLEAN
);

CREATE TABLE IF NOT EXISTS sandbox.fact_teacher_effectiveness_review (
    year SMALLINT NOT NULL,
    dist_name TEXT NOT NULL,
    school_name TEXT NOT NULL,
    score DOUBLE PRECISION,
    atot_completion_rate_designation TEXT,
    title_i_status TEXT
);

CREATE TABLE IF NOT EXISTS sandbox.fact_teacher_experience_review (
    year SMALLINT NOT NULL,
    dist_name TEXT NOT NULL,
    school_name TEXT NOT NULL,
    gender TEXT NOT NULL,
    race TEXT NOT NULL,
    ethnicity TEXT NOT NULL,
    sub_population TEXT NOT NULL,
    total_count NUMERIC(14,2),
    exp_count NUMERIC(14,2),
    exp_rate NUMERIC(8,4),
    inexp_count NUMERIC(14,2),
    inexp_rate NUMERIC(8,4)
);

CREATE TABLE IF NOT EXISTS sandbox.dim_geo_tract_review (
    geoid10 CHAR(11) PRIMARY KEY,
    county_fips CHAR(5),
    county_name TEXT,
    tract_name TEXT,
    state_abbr CHAR(2),
    state_fips CHAR(2),
    urbanicity TEXT
);

CREATE TABLE IF NOT EXISTS sandbox.fact_geo_population_review (
    geoid10 CHAR(11) NOT NULL,
    year SMALLINT NOT NULL,
    population_group TEXT NOT NULL,
    population_count INTEGER,
    population_share NUMERIC(8,4)
);

CREATE TABLE IF NOT EXISTS sandbox.fact_geo_opportunity_review (
    geoid10 CHAR(11) NOT NULL,
    year SMALLINT NOT NULL,
    metric_code TEXT NOT NULL,
    norm_scope TEXT NOT NULL,
    score NUMERIC(12,6),
    zscore NUMERIC(12,6),
    percentile NUMERIC(7,4),
    opportunity_level TEXT
);

CREATE TABLE IF NOT EXISTS sandbox.ref_al_district_to_county_review (
    district_name_normalized TEXT,
    county_fips CHAR(5),
    county_name TEXT,
    source_file TEXT,
    priority INTEGER
);

CREATE TABLE IF NOT EXISTS sandbox.ref_school_identity_crosswalk_review (
    ncessch CHAR(12),
    school_name TEXT,
    system_name TEXT,
    school_name_normalized TEXT,
    system_name_normalized TEXT,
    match_method TEXT,
    priority INTEGER
);

CREATE TABLE IF NOT EXISTS sandbox.bridge_school_geo_county_review (
    school_key BIGINT,
    school_year_start SMALLINT,
    school_year_label VARCHAR(9),
    dist_name TEXT,
    school_name TEXT,
    county_fips CHAR(5),
    county_name TEXT,
    match_method TEXT,
    strict_null_reason TEXT
);

CREATE TABLE IF NOT EXISTS sandbox.fact_school_outcomes_wide_review (
    year SMALLINT,
    dist_name TEXT,
    school_name TEXT,
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
    abs_other DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS sandbox.fact_school_outcomes_demographic_review (
    year SMALLINT,
    dist_name TEXT,
    school_name TEXT,
    indicator TEXT,
    subgroup TEXT,
    score DOUBLE PRECISION
);

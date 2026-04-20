CREATE OR REPLACE FUNCTION ref.normalize_label(v TEXT)
RETURNS TEXT
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT lower(regexp_replace(trim(coalesce(v,'')), '\\s+', ' ', 'g'))
$$;

CREATE TABLE IF NOT EXISTS ref.gender_canonical (
    canonical_value TEXT PRIMARY KEY,
    normalized_value TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS ref.race_canonical (
    canonical_value TEXT PRIMARY KEY,
    normalized_value TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS ref.ethnicity_canonical (
    canonical_value TEXT PRIMARY KEY,
    normalized_value TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS ref.staff_position_canonical (
    canonical_value TEXT PRIMARY KEY,
    normalized_value TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS ref.nces_locale_canonical (
    nces_locale_key SMALLSERIAL PRIMARY KEY,
    locale_code SMALLINT,
    locale_group VARCHAR(20),
    locale_subtype VARCHAR(20),
    canonical_value VARCHAR(40) NOT NULL UNIQUE,
    normalized_value VARCHAR(40) NOT NULL UNIQUE,
    is_unknown BOOLEAN NOT NULL DEFAULT FALSE,
    _created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    _updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ref.geo_population_group (
    population_group TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    description TEXT NOT NULL,
    display_order SMALLINT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS ref.geo_norm_scope (
    norm_scope TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    description TEXT NOT NULL,
    CONSTRAINT ck_geo_norm_scope CHECK (norm_scope IN ('nat', 'stt', 'met'))
);

CREATE TABLE IF NOT EXISTS ref.geo_opportunity_level (
    canonical_value TEXT PRIMARY KEY,
    normalized_value TEXT NOT NULL UNIQUE,
    level_rank SMALLINT NOT NULL UNIQUE,
    CONSTRAINT ck_geo_opportunity_level_rank CHECK (level_rank BETWEEN 1 AND 5)
);

CREATE TABLE IF NOT EXISTS ref.geo_domain (
    domain_code TEXT PRIMARY KEY,
    domain_name TEXT NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS ref.geo_subdomain (
    subdomain_code TEXT PRIMARY KEY,
    domain_code TEXT NOT NULL REFERENCES ref.geo_domain(domain_code),
    subdomain_name TEXT NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS ref.geo_metric (
    metric_code TEXT PRIMARY KEY,
    metric_level VARCHAR(12) NOT NULL,
    domain_code TEXT NOT NULL REFERENCES ref.geo_domain(domain_code),
    subdomain_code TEXT REFERENCES ref.geo_subdomain(subdomain_code),
    metric_name TEXT NOT NULL,
    metric_description TEXT,
    source_dataset TEXT NOT NULL,
    CONSTRAINT ck_geo_metric_level CHECK (metric_level IN ('index', 'domain', 'subdomain')),
    CONSTRAINT ck_geo_metric_source CHECK (source_dataset IN ('child_opportunity_index', 'subdomains_usa')),
    CONSTRAINT ck_geo_metric_subdomain_required CHECK (
      (metric_level = 'subdomain' AND subdomain_code IS NOT NULL)
      OR (metric_level IN ('index', 'domain') AND subdomain_code IS NULL)
    )
);

INSERT INTO ref.gender_canonical (canonical_value, normalized_value) VALUES
('All Gender', ref.normalize_label('All Gender')),
('Female', ref.normalize_label('Female')),
('Gender Not Specified', ref.normalize_label('Gender Not Specified')),
('Male', ref.normalize_label('Male'))
ON CONFLICT (canonical_value) DO UPDATE SET
    normalized_value = EXCLUDED.normalized_value;

INSERT INTO ref.race_canonical (canonical_value, normalized_value) VALUES
('All Race', ref.normalize_label('All Race')),
('American Indian/Alaska Native', ref.normalize_label('American Indian/Alaska Native')),
('Asian', ref.normalize_label('Asian')),
('Black or African American', ref.normalize_label('Black or African American')),
('Native Hawaiian/Pacific Islander', ref.normalize_label('Native Hawaiian/Pacific Islander')),
('Race Not Specified', ref.normalize_label('Race Not Specified')),
('Two or more races', ref.normalize_label('Two or more races')),
('White', ref.normalize_label('White'))
ON CONFLICT (canonical_value) DO UPDATE SET
    normalized_value = EXCLUDED.normalized_value;

INSERT INTO ref.ethnicity_canonical (canonical_value, normalized_value) VALUES
('All Ethnicity', ref.normalize_label('All Ethnicity')),
('Ethnicity Not Specified', ref.normalize_label('Ethnicity Not Specified')),
('Hispanic/Latino', ref.normalize_label('Hispanic/Latino')),
('Other Ethnicity', ref.normalize_label('Other Ethnicity'))
ON CONFLICT (canonical_value) DO UPDATE SET
    normalized_value = EXCLUDED.normalized_value;

INSERT INTO ref.nces_locale_canonical (locale_code, locale_group, locale_subtype, canonical_value, normalized_value, is_unknown) VALUES
(12, 'City', 'Mid-size', '12-City: Mid-size', '12-city: mid-size', FALSE),
(13, 'City', 'Small', '13-City: Small', '13-city: small', FALSE),
(21, 'Suburb', 'Large', '21-Suburb: Large', '21-suburb: large', FALSE),
(22, 'Suburb', 'Mid-size', '22-Suburb: Mid-size', '22-suburb: mid-size', FALSE),
(23, 'Suburb', 'Small', '23-Suburb: Small', '23-suburb: small', FALSE),
(31, 'Town', 'Fringe', '31-Town: Fringe', '31-town: fringe', FALSE),
(32, 'Town', 'Distant', '32-Town: Distant', '32-town: distant', FALSE),
(33, 'Town', 'Remote', '33-Town: Remote', '33-town: remote', FALSE),
(41, 'Rural', 'Fringe', '41-Rural: Fringe', '41-rural: fringe', FALSE),
(42, 'Rural', 'Distant', '42-Rural: Distant', '42-rural: distant', FALSE),
(43, 'Rural', 'Remote', '43-Rural: Remote', '43-rural: remote', FALSE),
(NULL, 'Unknown', 'Unknown', 'Unknown', 'unknown', TRUE)
ON CONFLICT (canonical_value) DO UPDATE SET
    locale_code = EXCLUDED.locale_code,
    locale_group = EXCLUDED.locale_group,
    locale_subtype = EXCLUDED.locale_subtype,
    normalized_value = EXCLUDED.normalized_value,
    is_unknown = EXCLUDED.is_unknown,
    _updated_at = now();

CREATE UNIQUE INDEX IF NOT EXISTS ux_nces_locale_code
    ON ref.nces_locale_canonical(locale_code)
    WHERE locale_code IS NOT NULL;

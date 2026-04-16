-- Canonical geo reference tables used by geographic ELT models.
-- Run in PostgreSQL.

CREATE SCHEMA IF NOT EXISTS ref;

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

INSERT INTO ref.geo_population_group (population_group, label, description, display_order) VALUES
('aian', 'American Indian and Alaska Native children', 'Number of children age 0-17 who are American Indian and Alaska Native alone.', 1),
('asian', 'Asian or Pacific Islander children', 'Number of children age 0-17 who are Asian or Pacific Islander alone.', 2),
('black', 'Black or African American children', 'Number of children age 0-17 who are Black or African American alone.', 3),
('hisp', 'Hispanic or Latino children', 'Number of children age 0-17 who are Hispanic or Latino.', 4),
('white', 'Non-Hispanic White children', 'Number of children age 0-17 who are White alone and not Hispanic or Latino.', 5),
('total', 'All children', 'Number of children age 0-17.', 6)
ON CONFLICT (population_group) DO UPDATE SET
    label = EXCLUDED.label,
    description = EXCLUDED.description,
    display_order = EXCLUDED.display_order;

INSERT INTO ref.geo_norm_scope (norm_scope, label, description) VALUES
('nat', 'Nationally normed', 'Metric is normalized against all census tracts nationally.'),
('stt', 'State normed', 'Metric is normalized against census tracts within the state.'),
('met', 'Metro normed', 'Metric is normalized against census tracts within the metro area.')
ON CONFLICT (norm_scope) DO UPDATE SET
    label = EXCLUDED.label,
    description = EXCLUDED.description;

INSERT INTO ref.geo_opportunity_level (canonical_value, normalized_value, level_rank) VALUES
('Very Low', 'very low', 1),
('Low', 'low', 2),
('Moderate', 'moderate', 3),
('High', 'high', 4),
('Very High', 'very high', 5)
ON CONFLICT (canonical_value) DO UPDATE SET
    normalized_value = EXCLUDED.normalized_value,
    level_rank = EXCLUDED.level_rank;

INSERT INTO ref.geo_domain (domain_code, domain_name, description) VALUES
('COI', 'Child Opportunity Index', 'Overall Child Opportunity Index.'),
('ED', 'Education domain', 'Education domain in the Child Opportunity Index framework.'),
('HE', 'Health and environment domain', 'Health and environment domain in the Child Opportunity Index framework.'),
('SE', 'Social and economic domain', 'Social and economic domain in the Child Opportunity Index framework.')
ON CONFLICT (domain_code) DO UPDATE SET
    domain_name = EXCLUDED.domain_name,
    description = EXCLUDED.description;

INSERT INTO ref.geo_subdomain (subdomain_code, domain_code, subdomain_name, description) VALUES
('ED_EC', 'ED', 'Early childhood education', 'Early childhood education subdomain.'),
('ED_EL', 'ED', 'Elementary education', 'Elementary education subdomain.'),
('ED_ER', 'ED', 'Educational resources', 'Educational resources subdomain.'),
('ED_SP', 'ED', 'Secondary and post-secondary education', 'Secondary and post-secondary education subdomain.'),
('HE_EP', 'HE', 'Pollution', 'Pollution subdomain.'),
('HE_HR', 'HE', 'Health resources', 'Health resources subdomain.'),
('HE_SE', 'HE', 'Safety-related resources', 'Safety-related resources subdomain.'),
('HE_HE', 'HE', 'Healthy environments', 'Healthy environments subdomain.'),
('SE_EI', 'SE', 'Concentrated socio-economic inequity', 'Concentrated socio-economic inequity subdomain.'),
('SE_EO', 'SE', 'Employment', 'Employment subdomain.'),
('SE_ER', 'SE', 'Economic resources', 'Economic resources subdomain.'),
('SE_HQ', 'SE', 'Housing resources', 'Housing resources subdomain.'),
('SE_SR', 'SE', 'Social resources', 'Social resources subdomain.'),
('SE_WL', 'SE', 'Wealth', 'Wealth subdomain.')
ON CONFLICT (subdomain_code) DO UPDATE SET
    domain_code = EXCLUDED.domain_code,
    subdomain_name = EXCLUDED.subdomain_name,
    description = EXCLUDED.description;

INSERT INTO ref.geo_metric (
    metric_code,
    metric_level,
    domain_code,
    subdomain_code,
    metric_name,
    metric_description,
    source_dataset
) VALUES
('COI', 'index', 'COI', NULL, 'Child Opportunity Index', 'Overall Child Opportunity Index metric.', 'child_opportunity_index'),
('ED', 'domain', 'ED', NULL, 'Education domain', 'Education domain metric.', 'child_opportunity_index'),
('HE', 'domain', 'HE', NULL, 'Health and environment domain', 'Health and environment domain metric.', 'child_opportunity_index'),
('SE', 'domain', 'SE', NULL, 'Social and economic domain', 'Social and economic domain metric.', 'child_opportunity_index'),
('ED_EC', 'subdomain', 'ED', 'ED_EC', 'Early childhood education', 'Early childhood education subdomain metric.', 'subdomains_usa'),
('ED_EL', 'subdomain', 'ED', 'ED_EL', 'Elementary education', 'Elementary education subdomain metric.', 'subdomains_usa'),
('ED_ER', 'subdomain', 'ED', 'ED_ER', 'Educational resources', 'Educational resources subdomain metric.', 'subdomains_usa'),
('ED_SP', 'subdomain', 'ED', 'ED_SP', 'Secondary and post-secondary education', 'Secondary and post-secondary education subdomain metric.', 'subdomains_usa'),
('HE_EP', 'subdomain', 'HE', 'HE_EP', 'Pollution', 'Pollution subdomain metric.', 'subdomains_usa'),
('HE_HR', 'subdomain', 'HE', 'HE_HR', 'Health resources', 'Health resources subdomain metric.', 'subdomains_usa'),
('HE_SE', 'subdomain', 'HE', 'HE_SE', 'Safety-related resources', 'Safety-related resources subdomain metric.', 'subdomains_usa'),
('HE_HE', 'subdomain', 'HE', 'HE_HE', 'Healthy environments', 'Healthy environments subdomain metric.', 'subdomains_usa'),
('SE_EI', 'subdomain', 'SE', 'SE_EI', 'Concentrated socio-economic inequity', 'Concentrated socio-economic inequity subdomain metric.', 'subdomains_usa'),
('SE_EO', 'subdomain', 'SE', 'SE_EO', 'Employment', 'Employment subdomain metric.', 'subdomains_usa'),
('SE_ER', 'subdomain', 'SE', 'SE_ER', 'Economic resources', 'Economic resources subdomain metric.', 'subdomains_usa'),
('SE_HQ', 'subdomain', 'SE', 'SE_HQ', 'Housing resources', 'Housing resources subdomain metric.', 'subdomains_usa'),
('SE_SR', 'subdomain', 'SE', 'SE_SR', 'Social resources', 'Social resources subdomain metric.', 'subdomains_usa'),
('SE_WL', 'subdomain', 'SE', 'SE_WL', 'Wealth', 'Wealth subdomain metric.', 'subdomains_usa')
ON CONFLICT (metric_code) DO UPDATE SET
    metric_level = EXCLUDED.metric_level,
    domain_code = EXCLUDED.domain_code,
    subdomain_code = EXCLUDED.subdomain_code,
    metric_name = EXCLUDED.metric_name,
    metric_description = EXCLUDED.metric_description,
    source_dataset = EXCLUDED.source_dataset;

CREATE INDEX IF NOT EXISTS idx_geo_subdomain_domain ON ref.geo_subdomain(domain_code);
CREATE INDEX IF NOT EXISTS idx_geo_metric_domain ON ref.geo_metric(domain_code);
CREATE INDEX IF NOT EXISTS idx_geo_metric_subdomain ON ref.geo_metric(subdomain_code);

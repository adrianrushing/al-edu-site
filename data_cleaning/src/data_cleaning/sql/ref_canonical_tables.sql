-- Canonical reference tables used by silver/core ELT.
-- Run in PostgreSQL.

CREATE SCHEMA IF NOT EXISTS ref;

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

INSERT INTO ref.staff_position_canonical (canonical_value, normalized_value) VALUES
('AAA Spec Ed', ref.normalize_label('AAA Spec Ed')),
('ARI Coach', ref.normalize_label('ARI Coach')),
('All SubPopulation', ref.normalize_label('All SubPopulation')),
('Assistant Coach', ref.normalize_label('Assistant Coach')),
('Assistive Technology Team', ref.normalize_label('Assistive Technology Team')),
('CNP Cafeteria Manager', ref.normalize_label('CNP Cafeteria Manager')),
('Counselor', ref.normalize_label('Counselor')),
('Driver Education Teacher', ref.normalize_label('Driver Education Teacher')),
('Drivers Ed Instructor', ref.normalize_label('Drivers Ed Instructor')),
('Head Coach', ref.normalize_label('Head Coach')),
('Instruction Assistant', ref.normalize_label('Instruction Assistant')),
('Instructional Technology Coach', ref.normalize_label('Instructional Technology Coach')),
('Librarian', ref.normalize_label('Librarian')),
('Other School Leader', ref.normalize_label('Other School Leader')),
('Physical Education Teacher', ref.normalize_label('Physical Education Teacher')),
('Pre-K Spec Ed', ref.normalize_label('Pre-K Spec Ed')),
('Principal', ref.normalize_label('Principal')),
('Psychometrist/Psychologist', ref.normalize_label('Psychometrist/Psychologist')),
('Registrar', ref.normalize_label('Registrar')),
('Secretary', ref.normalize_label('Secretary')),
('Speech Pathologist', ref.normalize_label('Speech Pathologist')),
('Teacher', ref.normalize_label('Teacher'))
ON CONFLICT (canonical_value) DO UPDATE SET
    normalized_value = EXCLUDED.normalized_value;

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

CREATE UNIQUE INDEX IF NOT EXISTS ux_nces_locale_code ON ref.nces_locale_canonical(locale_code) WHERE locale_code IS NOT NULL;

import type { BaselineResponse } from '@/lib/api';

export type DemoProfile = {
	description: string;
	id: 'high' | 'median' | 'low';
	label: string;
	baseline: BaselineResponse;
};

export const DEMO_MODEL_FEATURES = [
	'per_pupil_total_raw',
	'nces_poverty',
	'nces_freelunch',
	'exp_rate',
	'inexp_rate',
	'is_charter',
	'pct_american_indian_alaska_native',
	'pct_asian',
	'pct_black_or_african_american',
	'pct_native_hawaiian_pacific_islander',
	'pct_two_or_more_races',
	'pct_white',
	'nces_locale_type',
] as const;

export const DEMO_PROFILES: DemoProfile[] = [
	{
		id: 'high',
		label: 'High Achievement',
		description: 'Higher funding and lower poverty demonstrative profile.',
		baseline: {
			ach_all: 89.2,
			per_pupil_total_raw: 15200,
			nces_poverty: 0.22,
			nces_freelunch: 185,
			exp_rate: 88,
			inexp_rate: 12,
			nces_locale_type: 'Suburb',
			is_charter: 0,
			is_magnet: 0,
			pct_american_indian_alaska_native: 0.01,
			pct_asian: 0.11,
			pct_black_or_african_american: 0.24,
			pct_native_hawaiian_pacific_islander: 0.01,
			pct_two_or_more_races: 0.08,
			pct_white: 0.55,
		},
	},
	{
		id: 'median',
		label: 'Median Achievement',
		description: 'Middle-of-distribution demonstrative profile.',
		baseline: {
			ach_all: 71.4,
			per_pupil_total_raw: 12400,
			nces_poverty: 0.41,
			nces_freelunch: 365,
			exp_rate: 79,
			inexp_rate: 21,
			nces_locale_type: 'Town',
			is_charter: 0,
			is_magnet: 0,
			pct_american_indian_alaska_native: 0.01,
			pct_asian: 0.05,
			pct_black_or_african_american: 0.39,
			pct_native_hawaiian_pacific_islander: 0.01,
			pct_two_or_more_races: 0.07,
			pct_white: 0.47,
		},
	},
	{
		id: 'low',
		label: 'Low Achievement',
		description: 'Lower funding and higher poverty demonstrative profile.',
		baseline: {
			ach_all: 52.7,
			per_pupil_total_raw: 9800,
			nces_poverty: 0.64,
			nces_freelunch: 620,
			exp_rate: 68,
			inexp_rate: 32,
			nces_locale_type: 'Rural',
			is_charter: 0,
			is_magnet: 0,
			pct_american_indian_alaska_native: 0.02,
			pct_asian: 0.02,
			pct_black_or_african_american: 0.53,
			pct_native_hawaiian_pacific_islander: 0.01,
			pct_two_or_more_races: 0.06,
			pct_white: 0.36,
		},
	},
];

export const DEFAULT_DEMO_PROFILE_ID: DemoProfile['id'] = 'median';

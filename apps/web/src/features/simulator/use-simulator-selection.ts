import { useQuery } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';

import {
	fetchFilters,
	fetchSchoolSimulationMetadata,
	fetchSchools,
	type SchoolItem,
} from '@/lib/api';

import {
	DEFAULT_DEMO_PROFILE_ID,
	DEMO_PROFILES,
	type DemoProfile,
} from './demo-profiles';

const METADATA_STALE_TIME_MS = 60 * 1000;
const METADATA_GC_TIME_MS = 30 * 60 * 1000;
const SEARCH_DEBOUNCE_MS = 300;

export type SchoolDistrictGroup = {
	districtName: string;
	schools: SchoolItem[];
};

function groupSchoolsByDistrict(schools: SchoolItem[]): SchoolDistrictGroup[] {
	const latestBySchool = new Map<number, SchoolItem>();
	for (const school of schools) {
		const existing = latestBySchool.get(school.school_key);
		if (
			!existing ||
			school.school_year_start > existing.school_year_start
		) {
			latestBySchool.set(school.school_key, school);
		}
	}

	const districtMap = new Map<string, SchoolItem[]>();
	for (const school of latestBySchool.values()) {
		const districtName = school.dist_name?.trim() || 'Unknown District';
		const districtSchools = districtMap.get(districtName) ?? [];
		districtSchools.push(school);
		districtMap.set(districtName, districtSchools);
	}

	return Array.from(districtMap.entries())
		.sort(([a], [b]) => a.localeCompare(b))
		.map(([districtName, districtSchools]) => ({
			districtName,
			schools: districtSchools.sort((a, b) =>
				a.school_name.localeCompare(b.school_name),
			),
		}));
}

function useDebouncedValue(value: string, delayMs: number) {
	const [debounced, setDebounced] = useState(value);

	useEffect(() => {
		const handle = window.setTimeout(() => {
			setDebounced(value);
		}, delayMs);
		return () => window.clearTimeout(handle);
	}, [delayMs, value]);

	return debounced;
}

export function useSimulatorSelection() {
	const [selectionMode, setSelectionModeState] = useState<'demo' | 'school'>(
		'demo',
	);
	const [selectedYear, setSelectedYear] = useState<number | undefined>();
	const [schoolQuery, setSchoolQuery] = useState('');
	const [selectedSchoolKey, setSelectedSchoolKey] = useState<number | null>(
		null,
	);
	const [selectedDemoProfileId, setSelectedDemoProfileId] = useState<
		DemoProfile['id']
	>(DEFAULT_DEMO_PROFILE_ID);
	const [showMetadata, setShowMetadata] = useState(false);

	const debouncedSchoolQuery = useDebouncedValue(
		schoolQuery,
		SEARCH_DEBOUNCE_MS,
	);

	const filtersQuery = useQuery({
		queryKey: ['filters'],
		queryFn: fetchFilters,
		staleTime: METADATA_STALE_TIME_MS,
		gcTime: METADATA_GC_TIME_MS,
		refetchOnWindowFocus: false,
		enabled: selectionMode === 'school',
	});

	const schoolsQuery = useQuery({
		queryKey: ['simulator-schools', debouncedSchoolQuery],
		queryFn: () =>
			fetchSchools({
				q: debouncedSchoolQuery || undefined,
				limit: 200,
				offset: 0,
			}),
		staleTime: METADATA_STALE_TIME_MS,
		refetchOnWindowFocus: false,
		enabled: selectionMode === 'school',
	});

	const simulationMetadataQuery = useQuery({
		queryKey: [
			'school-simulation-metadata',
			selectedSchoolKey,
			selectedYear,
		],
		queryFn: () => {
			if (!selectedSchoolKey) {
				throw new Error('School is required');
			}
			return fetchSchoolSimulationMetadata(selectedSchoolKey, {
				year: selectedYear,
			});
		},
		staleTime: METADATA_STALE_TIME_MS,
		refetchOnWindowFocus: false,
		enabled: selectionMode === 'school' && selectedSchoolKey !== null,
	});

	const simulationMetadata = simulationMetadataQuery.data;
	const activeDemoProfile = DEMO_PROFILES.find(
		(profile) => profile.id === selectedDemoProfileId,
	);

	useEffect(() => {
		if (!selectedSchoolKey || selectedYear !== undefined) {
			return;
		}
		if (simulationMetadata?.selected_year != null) {
			setSelectedYear(simulationMetadata.selected_year);
		}
	}, [selectedSchoolKey, selectedYear, simulationMetadata]);

	const schoolsByDistrict = useMemo(
		() => groupSchoolsByDistrict(schoolsQuery.data ?? []),
		[schoolsQuery.data],
	);

	const yearOptions =
		selectionMode === 'school' && selectedSchoolKey !== null
			? (simulationMetadata?.available_years ?? [])
			: selectionMode === 'school'
				? (filtersQuery.data?.years ?? [])
				: [];

	const setSelectionMode = (mode: 'demo' | 'school') => {
		setSelectionModeState(mode);
		setShowMetadata(false);
		if (mode === 'demo') {
			setSelectedSchoolKey(null);
			setSelectedYear(undefined);
		}
	};

	const setSchoolSelection = (schoolKey: number | null) => {
		setSelectedSchoolKey(schoolKey);
		setSelectedYear(undefined);
		setShowMetadata(false);
	};

	return {
		activeDemoProfile,
		filtersQuery,
		selectionMode,
		schoolQuery,
		schoolsByDistrict,
		schoolsQuery,
		selectedDemoProfileId,
		selectedSchoolKey,
		selectedYear,
		setSelectionMode,
		setSelectedDemoProfileId,
		setSchoolQuery,
		setSchoolSelection,
		setSelectedYear,
		setShowMetadata,
		showMetadata,
		simulationMetadata,
		simulationMetadataQuery,
		yearOptions,
	};
}

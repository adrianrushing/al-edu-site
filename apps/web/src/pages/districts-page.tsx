import { useQuery } from '@tanstack/react-query';
import type { ColumnDef } from '@tanstack/react-table';
import { type ReactNode, useMemo } from 'react';

import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from '@/components/ui/card';
import { DataTable } from '@/components/ui/data-table';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { fetchFilters, fetchSchools } from '@/lib/api';
import type { DistrictSearch } from '@/pages/types';

const METADATA_STALE_TIME_MS = 10 * 60 * 1000;
const METADATA_GC_TIME_MS = 30 * 60 * 1000;

type DistrictsPageProps = {
	search: DistrictSearch;
	setSearch: (
		updater: (prev: DistrictSearch) => DistrictSearch,
		options?: { replace?: boolean },
	) => void;
};

export function DistrictsPage({ search, setSearch }: DistrictsPageProps) {
	const filtersQuery = useQuery({
		queryKey: ['filters'],
		queryFn: fetchFilters,
		staleTime: METADATA_STALE_TIME_MS,
		gcTime: METADATA_GC_TIME_MS,
	});

	const schoolsQuery = useQuery({
		queryKey: ['district-schools', search],
		queryFn: () =>
			fetchSchools({
				q: search.school || search.district,
				year: search.year,
				limit: 200,
				offset: 0,
			}),
		enabled: Boolean(search.school || search.district),
	});

	const schoolRows = schoolsQuery.data ?? [];
	const schoolColumns = useMemo<ColumnDef<Record<string, unknown>>[]>(
		() => [
			{
				accessorKey: 'dist_name',
				header: 'District',
				cell: ({ row }) => String(row.getValue('dist_name') ?? ''),
			},
			{
				accessorKey: 'school_name',
				header: 'School',
				cell: ({ row }) => String(row.getValue('school_name') ?? ''),
			},
			{
				accessorKey: 'school_year_start',
				header: 'Year',
				cell: ({ row }) =>
					String(row.getValue('school_year_start') ?? ''),
			},
			{
				accessorKey: 'school_key',
				header: 'School Key',
				cell: ({ row }) => String(row.getValue('school_key') ?? ''),
			},
		],
		[],
	);

	const updateDistrictSearch = (
		updater: (prev: DistrictSearch) => DistrictSearch,
	) => {
		setSearch((prev) => updater(prev), { replace: true });
	};

	return (
		<section className="space-y-4">
			<Card>
				<CardHeader>
					<CardTitle>District Drill Down</CardTitle>
					<CardDescription>
						Choose a district and year to load school-level records.
					</CardDescription>
				</CardHeader>
				<CardContent className="grid gap-3 md:grid-cols-3">
					<Field label="Year">
						<Select
							onChange={(event) =>
								updateDistrictSearch((prev) => ({
									...prev,
									year: event.target.value
										? Number(event.target.value)
										: undefined,
								}))
							}
							value={search.year?.toString() ?? ''}
						>
							<option value="">All years</option>
							{filtersQuery.data?.years.map((year) => (
								<option key={year} value={year}>
									{year}
								</option>
							))}
						</Select>
					</Field>

					<Field label="District">
						<Select
							onChange={(event) =>
								updateDistrictSearch((prev) => ({
									...prev,
									district: event.target.value || undefined,
								}))
							}
							value={search.district ?? ''}
						>
							<option value="">Select district</option>
							{filtersQuery.data?.districts.map((district) => (
								<option key={district} value={district}>
									{district}
								</option>
							))}
						</Select>
					</Field>

					<Field label="School Search">
						<Input
							onChange={(event) =>
								updateDistrictSearch((prev) => ({
									...prev,
									school: event.target.value || undefined,
								}))
							}
							placeholder="Search school name"
							value={search.school ?? ''}
						/>
					</Field>
				</CardContent>
			</Card>

			<Card className="min-w-0">
				<CardHeader>
					<CardTitle>Schools</CardTitle>
					<CardDescription>
						{schoolsQuery.error instanceof Error
							? schoolsQuery.error.message
							: `${schoolRows.length} rows loaded`}
					</CardDescription>
				</CardHeader>
				<CardContent className="min-w-0">
					<DataTable
						columns={schoolColumns}
						data={schoolRows as Record<string, unknown>[]}
						emptyMessage="Select a district or enter a school name to load results."
					/>
				</CardContent>
			</Card>
		</section>
	);
}

function Field({ label, children }: { label: string; children: ReactNode }) {
	return (
		<div className="grid gap-1 text-sm">
			<span className="font-medium text-muted-foreground">{label}</span>
			{children}
		</div>
	);
}

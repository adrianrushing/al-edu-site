import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from '@/components/ui/card';
import { Select } from '@/components/ui/select';
import {
	type DistrictRankingItem,
	type DistrictSchoolItem,
	fetchDistrictRankings,
	fetchDistrictSchools,
	fetchFilters,
	fetchSchoolPerformanceTrend,
} from '@/lib/api';
import type { RankingsSearch } from '@/pages/types';

const DEFAULT_RANKINGS_LIMIT = 25;
const TREND_LOOKBACK_YEARS = 5;
const MILLISECONDS_PER_SECOND = 1000;
const SECONDS_PER_MINUTE = 60;
const METADATA_GC_MINUTES = 30;
const METADATA_STALE_TIME_MS =
	10 * SECONDS_PER_MINUTE * MILLISECONDS_PER_SECOND;
const METADATA_GC_TIME_MS =
	METADATA_GC_MINUTES * SECONDS_PER_MINUTE * MILLISECONDS_PER_SECOND;

type RankingsPageProps = {
	search: RankingsSearch;
	setSearch: (
		updater: (prev: RankingsSearch) => RankingsSearch,
		options?: { replace?: boolean },
	) => void;
};

export function RankingsPage({ search, setSearch }: RankingsPageProps) {
	const filtersQuery = useQuery({
		queryKey: ['filters'],
		queryFn: fetchFilters,
		staleTime: METADATA_STALE_TIME_MS,
		gcTime: METADATA_GC_TIME_MS,
	});

	useEffect(() => {
		if (search.year || !filtersQuery.data?.years.length) {
			return;
		}
		const latestYear = Math.max(...filtersQuery.data.years);
		setSearch(
			(prev) => ({
				...prev,
				year: latestYear,
				limit: prev.limit ?? DEFAULT_RANKINGS_LIMIT,
				cursor: undefined,
			}),
			{ replace: true },
		);
	}, [filtersQuery.data, search.year, setSearch]);

	const rankingsQuery = useQuery({
		queryKey: [
			'district-rankings',
			search.year,
			search.limit,
			search.cursor,
		],
		queryFn: () =>
			fetchDistrictRankings({
				year: search.year,
				limit: search.limit ?? DEFAULT_RANKINGS_LIMIT,
				cursor: search.cursor,
			}),
		enabled: search.year !== undefined,
	});

	const nextCursor = rankingsQuery.data?.next_cursor;

	return (
		<section className="space-y-4">
			<Card>
				<CardHeader>
					<CardTitle>District Funding Rankings</CardTitle>
					<CardDescription>
						Ranked by average per-pupil funding. Expand districts to
						lazy-load schools, then expand schools for multi-year
						performance.
					</CardDescription>
				</CardHeader>
				<CardContent className="flex flex-wrap items-end gap-3">
					<div className="grid gap-1 text-sm">
						<span className="font-medium text-muted-foreground">
							Year
						</span>
						<Select
							onChange={(event) =>
								setSearch(
									(prev) => ({
										...prev,
										year: event.target.value
											? Number(event.target.value)
											: undefined,
										cursor: undefined,
									}),
									{ replace: true },
								)
							}
							value={search.year?.toString() ?? ''}
						>
							<option value="">Select year</option>
							{filtersQuery.data?.years.map((year) => (
								<option key={year} value={year}>
									{year}
								</option>
							))}
						</Select>
					</div>

					<div className="grid gap-1 text-sm">
						<span className="font-medium text-muted-foreground">
							Rows
						</span>
						<Select
							onChange={(event) =>
								setSearch(
									(prev) => ({
										...prev,
										limit: Number(event.target.value),
										cursor: undefined,
									}),
									{ replace: true },
								)
							}
							value={String(
								search.limit ?? DEFAULT_RANKINGS_LIMIT,
							)}
						>
							<option value="10">10</option>
							<option value="25">25</option>
							<option value="50">50</option>
						</Select>
					</div>

					<div className="flex gap-2">
						<Button
							disabled={!search.cursor}
							onClick={() =>
								setSearch(
									(prev) => ({ ...prev, cursor: undefined }),
									{
										replace: true,
									},
								)
							}
							variant="outline"
						>
							First Page
						</Button>
						<Button
							disabled={!nextCursor || rankingsQuery.isFetching}
							onClick={() =>
								setSearch(
									(prev) => ({
										...prev,
										cursor: nextCursor ?? undefined,
									}),
									{ replace: true },
								)
							}
						>
							Next Page
						</Button>
					</div>
				</CardContent>
			</Card>

			<Card>
				<CardHeader>
					<CardTitle>Districts</CardTitle>
					<CardDescription>
						{rankingsQuery.error instanceof Error
							? rankingsQuery.error.message
							: `${rankingsQuery.data?.items.length ?? 0} districts loaded`}
					</CardDescription>
				</CardHeader>
				<CardContent className="overflow-x-auto">
					<table className="w-full min-w-[720px] text-sm">
						<thead>
							<tr className="border-b text-left">
								<th className="px-2 py-2">Expand</th>
								<th className="px-2 py-2">Rank</th>
								<th className="px-2 py-2">District</th>
								<th className="px-2 py-2">Avg Funding</th>
								<th className="px-2 py-2">Avg Achievement</th>
								<th className="px-2 py-2">Schools</th>
							</tr>
						</thead>
						<tbody>
							{rankingsQuery.data?.items.map((district) => (
								<DistrictRow
									district={district}
									key={`${district.year}-${district.district_key}`}
									year={search.year}
								/>
							))}
						</tbody>
					</table>
				</CardContent>
			</Card>
		</section>
	);
}

function DistrictRow({
	district,
	year,
}: {
	district: DistrictRankingItem;
	year?: number;
}) {
	const [expanded, setExpanded] = useState(false);

	const schoolsQuery = useQuery({
		queryKey: ['ranking-district-schools', district.district_key, year],
		queryFn: () =>
			fetchDistrictSchools(district.district_key, {
				year,
				limit: 100,
			}),
		enabled: expanded,
	});

	return (
		<>
			<tr className="border-b align-top">
				<td className="px-2 py-2">
					<Button
						onClick={() => setExpanded((v) => !v)}
						size="sm"
						variant="ghost"
					>
						{expanded ? 'Hide' : 'Show'}
					</Button>
				</td>
				<td className="px-2 py-2">{district.funding_rank}</td>
				<td className="px-2 py-2 font-medium">
					{district.district_name}
				</td>
				<td className="px-2 py-2">
					{formatCurrency(district.avg_per_pupil_funding)}
				</td>
				<td className="px-2 py-2">
					{formatNumber(district.avg_achievement)}
				</td>
				<td className="px-2 py-2">{district.school_count}</td>
			</tr>
			{expanded && (
				<tr className="border-b bg-muted/20">
					<td className="px-2 py-3" colSpan={6}>
						{schoolsQuery.error instanceof Error ? (
							<p className="text-sm text-red-600">
								{schoolsQuery.error.message}
							</p>
						) : schoolsQuery.isLoading ? (
							<p className="text-sm text-muted-foreground">
								Loading schools...
							</p>
						) : (
							<div className="space-y-2">
								<table className="w-full text-sm">
									<thead>
										<tr className="border-b text-left">
											<th className="px-2 py-1">
												Expand
											</th>
											<th className="px-2 py-1">
												School
											</th>
											<th className="px-2 py-1">
												Funding
											</th>
											<th className="px-2 py-1">
												Achievement
											</th>
										</tr>
									</thead>
									<tbody>
										{schoolsQuery.data?.items.map(
											(school) => (
												<SchoolRow
													key={`${school.school_key}`}
													school={school}
													year={year}
												/>
											),
										)}
									</tbody>
								</table>
								{schoolsQuery.data?.next_cursor && (
									<p className="text-xs text-muted-foreground">
										More schools are available. Increase row
										limits in API/UI if needed.
									</p>
								)}
							</div>
						)}
					</td>
				</tr>
			)}
		</>
	);
}

function SchoolRow({
	school,
	year,
}: {
	school: DistrictSchoolItem;
	year?: number;
}) {
	const [expanded, setExpanded] = useState(false);

	const trendQuery = useQuery({
		queryKey: ['ranking-school-trend', school.school_key, year],
		queryFn: () =>
			fetchSchoolPerformanceTrend(school.school_key, {
				from_year: year ? year - TREND_LOOKBACK_YEARS : undefined,
				to_year: year,
			}),
		enabled: expanded,
	});

	return (
		<>
			<tr className="border-b align-top">
				<td className="px-2 py-1">
					<Button
						onClick={() => setExpanded((v) => !v)}
						size="sm"
						variant="ghost"
					>
						{expanded ? 'Hide' : 'Trend'}
					</Button>
				</td>
				<td className="px-2 py-1">{school.school_name}</td>
				<td className="px-2 py-1">
					{formatCurrency(school.per_pupil_total_raw)}
				</td>
				<td className="px-2 py-1">{formatNumber(school.ach_all)}</td>
			</tr>
			{expanded && (
				<tr className="border-b bg-card">
					<td className="px-2 py-2" colSpan={4}>
						{trendQuery.error instanceof Error ? (
							<p className="text-xs text-red-600">
								{trendQuery.error.message}
							</p>
						) : trendQuery.isLoading ? (
							<p className="text-xs text-muted-foreground">
								Loading school performance history...
							</p>
						) : (
							<table className="w-full text-xs">
								<thead>
									<tr className="border-b text-left">
										<th className="px-2 py-1">Year</th>
										<th className="px-2 py-1">Funding</th>
										<th className="px-2 py-1">Ach</th>
										<th className="px-2 py-1">Growth</th>
										<th className="px-2 py-1">
											Absenteeism
										</th>
									</tr>
								</thead>
								<tbody>
									{trendQuery.data?.points.map((point) => (
										<tr
											key={`${school.school_key}-${point.year}`}
										>
											<td className="px-2 py-1">
												{point.year}
											</td>
											<td className="px-2 py-1">
												{formatCurrency(
													point.per_pupil_total_raw,
												)}
											</td>
											<td className="px-2 py-1">
												{formatNumber(point.ach_all)}
											</td>
											<td className="px-2 py-1">
												{formatNumber(point.grw_all)}
											</td>
											<td className="px-2 py-1">
												{formatNumber(point.abs_all)}
											</td>
										</tr>
									))}
								</tbody>
							</table>
						)}
					</td>
				</tr>
			)}
		</>
	);
}

function formatCurrency(value: number | null) {
	if (value === null || Number.isNaN(value)) {
		return '-';
	}
	return new Intl.NumberFormat('en-US', {
		style: 'currency',
		currency: 'USD',
		maximumFractionDigits: 0,
	}).format(value);
}

function formatNumber(value: number | null) {
	if (value === null || Number.isNaN(value)) {
		return '-';
	}
	return value.toFixed(2);
}

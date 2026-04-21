import { useQuery } from '@tanstack/react-query';
import type { ColumnDef } from '@tanstack/react-table';
import {
	type ReactNode,
	useCallback,
	useEffect,
	useMemo,
	useRef,
	useState,
} from 'react';

import { Button, buttonVariants } from '@/components/ui/button';
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
import {
	fetchDatasets,
	fetchFilters,
	fetchPreview,
	getDownloadUrl,
} from '@/lib/api';
import type { DownloadSearch } from '@/pages/types';

const INPUT_DEBOUNCE_MS = 300;
const METADATA_STALE_TIME_MS = 10 * 60 * 1000;
const METADATA_GC_TIME_MS = 30 * 60 * 1000;

type DownloadPageProps = {
	search: DownloadSearch;
	setSearch: (
		updater: (prev: DownloadSearch) => DownloadSearch,
		options?: { replace?: boolean },
	) => void;
};

export function DownloadPage({ search, setSearch }: DownloadPageProps) {
	const [draftFilters, setDraftFilters] = useState<DownloadSearch>(() => ({
		...search,
	}));
	const pendingApplyTimeoutRef = useRef<number | null>(null);

	useEffect(() => {
		setDraftFilters({ ...search });
	}, [search]);

	const datasetsQuery = useQuery({
		queryKey: ['datasets'],
		queryFn: fetchDatasets,
		staleTime: METADATA_STALE_TIME_MS,
		gcTime: METADATA_GC_TIME_MS,
	});
	const filtersQuery = useQuery({
		queryKey: ['filters'],
		queryFn: fetchFilters,
		staleTime: METADATA_STALE_TIME_MS,
		gcTime: METADATA_GC_TIME_MS,
	});

	const previewQuery = useQuery({
		queryKey: ['preview', search],
		queryFn: () =>
			fetchPreview(search.dataset ?? 'teacher_effectiveness', search),
		enabled: Boolean(search.dataset),
	});

	const effectiveDataset =
		search.dataset ??
		datasetsQuery.data?.[0]?.key ??
		'teacher_effectiveness';
	const downloadUrl = getDownloadUrl(effectiveDataset, search);
	const previewRows = previewQuery.data?.rows ?? [];

	const tableColumns = useMemo<ColumnDef<Record<string, unknown>>[]>(() => {
		if (previewRows.length === 0) {
			return [];
		}

		return Object.keys(previewRows[0]).map((column) => ({
			accessorKey: column,
			header: column,
			cell: ({ row }) => String(row.getValue(column) ?? ''),
		}));
	}, [previewRows]);

	const clearPendingApply = useCallback(() => {
		if (pendingApplyTimeoutRef.current !== null) {
			window.clearTimeout(pendingApplyTimeoutRef.current);
			pendingApplyTimeoutRef.current = null;
		}
	}, []);

	useEffect(() => {
		return () => {
			clearPendingApply();
		};
	}, [clearPendingApply]);

	const applyDraftFilters = (
		nextDraft: DownloadSearch,
		options?: { replace?: boolean },
	) => {
		setSearch(
			(prev) => ({
				...prev,
				...nextDraft,
				dataset: nextDraft.dataset ?? effectiveDataset,
				limit: nextDraft.limit ?? 50,
				offset: 0,
			}),
			options,
		);
	};

	const updateDraftAndApply = <K extends keyof DownloadSearch>(
		key: K,
		value: DownloadSearch[K],
		options?: { debounceMs?: number },
	) => {
		const nextDraft = {
			...draftFilters,
			[key]: value,
		};

		setDraftFilters(nextDraft);
		clearPendingApply();

		const debounceMs = options?.debounceMs ?? 0;
		if (debounceMs > 0) {
			pendingApplyTimeoutRef.current = window.setTimeout(() => {
				applyDraftFilters(nextDraft, { replace: true });
				pendingApplyTimeoutRef.current = null;
			}, debounceMs);
			return;
		}

		applyDraftFilters(nextDraft);
	};

	const applyFilters = () => {
		clearPendingApply();
		applyDraftFilters(draftFilters);
	};

	const resetFilters = () => {
		const resetState: DownloadSearch = {
			dataset: effectiveDataset,
			limit: 50,
			offset: 0,
		};

		clearPendingApply();
		setDraftFilters(resetState);
		setSearch(() => resetState);
	};

	const isBusyError =
		previewQuery.error instanceof Error &&
		previewQuery.error.message.toLowerCase().includes('busy');

	const pageSize = search.limit ?? 50;
	const offset = search.offset ?? 0;
	const currentCount = previewQuery.data?.row_count ?? 0;
	const canPreviousPage = offset > 0;
	const canNextPage = currentCount === pageSize;
	const rangeStart = currentCount > 0 ? offset + 1 : 0;
	const rangeEnd = offset + currentCount;

	const goToPreviousPage = () => {
		if (!canPreviousPage) {
			return;
		}

		setSearch((prev) => ({
			...prev,
			offset: Math.max((prev.offset ?? 0) - (prev.limit ?? 50), 0),
		}));
	};

	const goToNextPage = () => {
		if (!canNextPage) {
			return;
		}

		setSearch((prev) => ({
			...prev,
			offset: (prev.offset ?? 0) + (prev.limit ?? 50),
		}));
	};

	return (
		<div className="-mx-4 grid gap-4 px-4 lg:grid-cols-[300px_1fr] lg:px-6">
			<aside className="lg:sticky lg:top-6 lg:h-[calc(100vh-2rem)]">
				<Card className="h-full overflow-y-auto">
					<CardHeader>
						<CardTitle>Filters</CardTitle>
						<CardDescription>
							Use this left panel as your query navbar. Preview
							updates automatically as you type.
						</CardDescription>
					</CardHeader>
					<CardContent className="space-y-3">
						<Field label="Dataset">
							<Select
								onChange={(event) =>
									updateDraftAndApply(
										'dataset',
										event.target.value,
									)
								}
								value={draftFilters.dataset ?? effectiveDataset}
							>
								{datasetsQuery.data?.map((dataset) => (
									<option
										key={dataset.key}
										value={dataset.key}
									>
										{dataset.key}
									</option>
								))}
							</Select>
						</Field>

						<Field label="Year">
							<Select
								onChange={(event) =>
									updateDraftAndApply(
										'year',
										event.target.value
											? Number(event.target.value)
											: undefined,
									)
								}
								value={draftFilters.year?.toString() ?? ''}
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
							<Input
								onChange={(event) =>
									updateDraftAndApply(
										'district',
										event.target.value || undefined,
										{
											debounceMs: INPUT_DEBOUNCE_MS,
										},
									)
								}
								placeholder="Mobile County"
								value={draftFilters.district ?? ''}
							/>
						</Field>

						<Field label="School">
							<Input
								onChange={(event) =>
									updateDraftAndApply(
										'school',
										event.target.value || undefined,
										{
											debounceMs: INPUT_DEBOUNCE_MS,
										},
									)
								}
								placeholder="Baker High School"
								value={draftFilters.school ?? ''}
							/>
						</Field>

						<Field label="School Key">
							<Input
								onChange={(event) =>
									updateDraftAndApply(
										'school_key',
										event.target.value
											? Number(event.target.value)
											: undefined,
										{
											debounceMs: INPUT_DEBOUNCE_MS,
										},
									)
								}
								placeholder="7941"
								value={
									draftFilters.school_key?.toString() ?? ''
								}
							/>
						</Field>

						<Field label="Preview Rows">
							<Select
								onChange={(event) =>
									updateDraftAndApply(
										'limit',
										Number(event.target.value),
									)
								}
								value={String(draftFilters.limit ?? 50)}
							>
								<option value="25">25</option>
								<option value="50">50</option>
								<option value="100">100</option>
								<option value="250">250</option>
							</Select>
						</Field>

						<div className="flex flex-wrap gap-2 pt-2">
							<Button onClick={resetFilters} variant="outline">
								Reset
							</Button>
							<Button onClick={applyFilters}>Apply Now</Button>
							<a
								className={buttonVariants({ variant: 'ghost' })}
								href={downloadUrl}
							>
								Download CSV
							</a>
						</div>
					</CardContent>
				</Card>
			</aside>

			<Card className="min-w-0">
				<CardHeader>
					<CardTitle>Preview</CardTitle>
					<CardDescription>
						{previewQuery.error instanceof Error
							? previewQuery.error.message
							: `Showing ${previewQuery.data?.row_count ?? 0} rows`}
					</CardDescription>
					{isBusyError && (
						<p className="text-xs font-medium text-primary">
							The database is busy. Wait a moment, then click
							Apply Now or edit a filter again.
						</p>
					)}
				</CardHeader>
				<CardContent className="min-w-0">
					<DataTable
						columns={tableColumns}
						data={previewRows}
						emptyMessage="No preview rows yet. Adjust filters to load results."
						pagination={{
							canPreviousPage:
								canPreviousPage && !previewQuery.isFetching,
							canNextPage:
								canNextPage && !previewQuery.isFetching,
							onPreviousPage: goToPreviousPage,
							onNextPage: goToNextPage,
							summary:
								currentCount > 0
									? `Rows ${rangeStart}-${rangeEnd}`
									: 'No rows in current page',
						}}
					/>
				</CardContent>
			</Card>
		</div>
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

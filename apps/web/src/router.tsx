import {
    QueryClient,
    QueryClientProvider,
    useQuery,
} from "@tanstack/react-query";
import {
    createRootRoute,
    createRoute,
    createRouter,
    Link,
    Outlet,
    RouterProvider,
    useNavigate,
} from "@tanstack/react-router";
import type { ColumnDef } from "@tanstack/react-table";
import { type ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { DataTable } from "@/components/ui/data-table";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import {
    fetchDatasets,
    fetchFilters,
    fetchPreview,
    fetchSchools,
    getDownloadUrl,
} from "@/lib/api";

const queryClient = new QueryClient();
const INPUT_DEBOUNCE_MS = 300;

const rootRoute = createRootRoute({
    component: () => (
        <div className="w-full px-4 py-6 sm:px-6 lg:px-8">
            <header className="mb-6 flex flex-col gap-3 rounded-lg border bg-card/80 p-5 backdrop-blur-sm md:flex-row md:items-center md:justify-between">
                <div>
                    <h1 className="text-2xl font-black tracking-tight">
                        EFLT Data Download Console
                    </h1>
                    <p className="text-sm text-muted-foreground">
                        Filter state education data and export clean CSVs in
                        seconds.
                    </p>
                </div>
                <nav className="flex gap-2">
                    <Link
                        to="/"
                        className="rounded-md px-3 py-2 text-sm font-medium hover:bg-muted data-[status=active]:bg-muted"
                    >
                        Home
                    </Link>
                    <Link
                        to="/download"
                        search={{ limit: 50, offset: 0 }}
                        className="rounded-md px-3 py-2 text-sm font-medium hover:bg-muted data-[status=active]:bg-muted"
                    >
                        Download
                    </Link>
                    <Link
                        to="/districts"
                        search={{}}
                        className="rounded-md px-3 py-2 text-sm font-medium hover:bg-muted data-[status=active]:bg-muted"
                    >
                        Districts
                    </Link>
                </nav>
            </header>
            <Outlet />
        </div>
    ),
});

const homeRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "/",
    component: HomePage,
});

const downloadSearch = z.object({
    dataset: z.string().optional(),
    year: z.coerce.number().optional(),
    district: z.string().optional(),
    school: z.string().optional(),
    school_key: z.coerce.number().optional(),
    gender: z.string().optional(),
    race: z.string().optional(),
    ethnicity: z.string().optional(),
    sub_population: z.string().optional(),
    grade: z.string().optional(),
    limit: z.coerce.number().optional().default(50),
    offset: z.coerce.number().optional().default(0),
});

type DownloadSearch = z.infer<typeof downloadSearch>;

const downloadRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "/download",
    validateSearch: (search) => downloadSearch.parse(search),
    component: DownloadPage,
});

const districtSearch = z.object({
    year: z.coerce.number().optional(),
    district: z.string().optional(),
    school: z.string().optional(),
});

type DistrictSearch = z.infer<typeof districtSearch>;

const districtsRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "/districts",
    validateSearch: (search) => districtSearch.parse(search),
    component: DistrictsPage,
});

const routeTree = rootRoute.addChildren([
    homeRoute,
    downloadRoute,
    districtsRoute,
]);

const router = createRouter({ routeTree });

declare module "@tanstack/react-router" {
    interface Register {
        router: typeof router;
    }
}

export function AppRouter() {
    return (
        <QueryClientProvider client={queryClient}>
            <RouterProvider router={router} />
        </QueryClientProvider>
    );
}

function HomePage() {
    const datasetsQuery = useQuery({
        queryKey: ["datasets"],
        queryFn: fetchDatasets,
    });

    return (
        <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {datasetsQuery.data?.map((dataset) => (
                <Card key={dataset.key}>
                    <CardHeader>
                        <CardTitle>
                            {dataset.key.replaceAll("_", " ")}
                        </CardTitle>
                        <CardDescription>{dataset.description}</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <Link
                            to="/download"
                            search={{
                                dataset: dataset.key,
                                limit: 50,
                                offset: 0,
                            }}
                            className="text-sm font-semibold text-primary hover:underline"
                        >
                            Open dataset
                        </Link>
                    </CardContent>
                </Card>
            ))}
            {!datasetsQuery.data && (
                <Card>
                    <CardContent className="pt-6 text-sm text-muted-foreground">
                        Loading datasets...
                    </CardContent>
                </Card>
            )}
        </section>
    );
}

function DownloadPage() {
    const search = downloadRoute.useSearch();
    const navigate = useNavigate({ from: "/download" });

    const [draftFilters, setDraftFilters] = useState<DownloadSearch>(() => ({
        ...search,
    }));
    const pendingApplyTimeoutRef = useRef<number | null>(null);

    useEffect(() => {
        setDraftFilters({ ...search });
    }, [search]);

    const datasetsQuery = useQuery({
        queryKey: ["datasets"],
        queryFn: fetchDatasets,
    });
    const filtersQuery = useQuery({
        queryKey: ["filters"],
        queryFn: fetchFilters,
    });

    const previewQuery = useQuery({
        queryKey: ["preview", search],
        queryFn: () =>
            fetchPreview(search.dataset ?? "teacher_effectiveness", search),
        enabled: Boolean(search.dataset),
    });

    const effectiveDataset =
        search.dataset ??
        datasetsQuery.data?.[0]?.key ??
        "teacher_effectiveness";
    const downloadUrl = getDownloadUrl(effectiveDataset, search);
    const previewRows = previewQuery.data?.rows ?? [];

    const tableColumns = useMemo<ColumnDef<Record<string, unknown>>[]>(() => {
        if (previewRows.length === 0) {
            return [];
        }

        return Object.keys(previewRows[0]).map((column) => ({
            accessorKey: column,
            header: column,
            cell: ({ row }) => String(row.getValue(column) ?? ""),
        }));
    }, [previewRows]);

    const clearPendingApply = () => {
        if (pendingApplyTimeoutRef.current !== null) {
            window.clearTimeout(pendingApplyTimeoutRef.current);
            pendingApplyTimeoutRef.current = null;
        }
    };

    useEffect(() => {
        return () => {
            clearPendingApply();
        };
    }, []);

    const applyDraftFilters = (
        nextDraft: DownloadSearch,
        options?: { replace?: boolean },
    ) => {
        navigate({
            replace: options?.replace,
            search: (prev) => ({
                ...prev,
                ...nextDraft,
                dataset: nextDraft.dataset ?? effectiveDataset,
                limit: nextDraft.limit ?? 50,
                offset: 0,
            }),
        });
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
        navigate({ search: resetState });
    };

    const isBusyError =
        previewQuery.error instanceof Error &&
        previewQuery.error.message.toLowerCase().includes("busy");

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

        navigate({
            search: (prev) => ({
                ...prev,
                offset: Math.max((prev.offset ?? 0) - (prev.limit ?? 50), 0),
            }),
        });
    };

    const goToNextPage = () => {
        if (!canNextPage) {
            return;
        }

        navigate({
            search: (prev) => ({
                ...prev,
                offset: (prev.offset ?? 0) + (prev.limit ?? 50),
            }),
        });
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
                                value={draftFilters.dataset ?? effectiveDataset}
                                onChange={(event) =>
                                    updateDraftAndApply(
                                        "dataset",
                                        event.target.value,
                                    )
                                }
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
                                value={draftFilters.year?.toString() ?? ""}
                                onChange={(event) =>
                                    updateDraftAndApply(
                                        "year",
                                        event.target.value
                                            ? Number(event.target.value)
                                            : undefined,
                                    )
                                }
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
                                value={draftFilters.district ?? ""}
                                placeholder="Mobile County"
                                onChange={(event) =>
                                    updateDraftAndApply(
                                        "district",
                                        event.target.value || undefined,
                                        {
                                            debounceMs: INPUT_DEBOUNCE_MS,
                                        },
                                    )
                                }
                            />
                        </Field>

                        <Field label="School">
                            <Input
                                value={draftFilters.school ?? ""}
                                placeholder="Baker High School"
                                onChange={(event) =>
                                    updateDraftAndApply(
                                        "school",
                                        event.target.value || undefined,
                                        {
                                            debounceMs: INPUT_DEBOUNCE_MS,
                                        },
                                    )
                                }
                            />
                        </Field>

                        <Field label="School Key">
                            <Input
                                value={
                                    draftFilters.school_key?.toString() ?? ""
                                }
                                placeholder="7941"
                                onChange={(event) =>
                                    updateDraftAndApply(
                                        "school_key",
                                        event.target.value
                                            ? Number(event.target.value)
                                            : undefined,
                                        {
                                            debounceMs: INPUT_DEBOUNCE_MS,
                                        },
                                    )
                                }
                            />
                        </Field>

                        <Field label="Preview Rows">
                            <Select
                                value={String(draftFilters.limit ?? 50)}
                                onChange={(event) =>
                                    updateDraftAndApply(
                                        "limit",
                                        Number(event.target.value),
                                    )
                                }
                            >
                                <option value="25">25</option>
                                <option value="50">50</option>
                                <option value="100">100</option>
                                <option value="250">250</option>
                            </Select>
                        </Field>

                        <div className="flex flex-wrap gap-2 pt-2">
                            <Button variant="outline" onClick={resetFilters}>
                                Reset
                            </Button>
                            <Button onClick={applyFilters}>Apply Now</Button>
                            <a href={downloadUrl}>
                                <Button variant="ghost">Download CSV</Button>
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
                                    : "No rows in current page",
                        }}
                    />
                </CardContent>
            </Card>
        </div>
    );
}

function DistrictsPage() {
    const search = districtsRoute.useSearch();
    const navigate = useNavigate({ from: "/districts" });

    const filtersQuery = useQuery({
        queryKey: ["filters"],
        queryFn: fetchFilters,
    });

    const schoolsQuery = useQuery({
        queryKey: ["district-schools", search],
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
                accessorKey: "dist_name",
                header: "District",
                cell: ({ row }) => String(row.getValue("dist_name") ?? ""),
            },
            {
                accessorKey: "school_name",
                header: "School",
                cell: ({ row }) => String(row.getValue("school_name") ?? ""),
            },
            {
                accessorKey: "school_year_start",
                header: "Year",
                cell: ({ row }) =>
                    String(row.getValue("school_year_start") ?? ""),
            },
            {
                accessorKey: "school_key",
                header: "School Key",
                cell: ({ row }) => String(row.getValue("school_key") ?? ""),
            },
        ],
        [],
    );

    const updateDistrictSearch = (
        updater: (prev: DistrictSearch) => DistrictSearch,
    ) => {
        navigate({
            replace: true,
            search: (prev) => updater(prev as DistrictSearch),
        });
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
                            value={search.year?.toString() ?? ""}
                            onChange={(event) =>
                                updateDistrictSearch((prev) => ({
                                    ...prev,
                                    year: event.target.value
                                        ? Number(event.target.value)
                                        : undefined,
                                }))
                            }
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
                            value={search.district ?? ""}
                            onChange={(event) =>
                                updateDistrictSearch((prev) => ({
                                    ...prev,
                                    district: event.target.value || undefined,
                                }))
                            }
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
                            value={search.school ?? ""}
                            placeholder="Search school name"
                            onChange={(event) =>
                                updateDistrictSearch((prev) => ({
                                    ...prev,
                                    school: event.target.value || undefined,
                                }))
                            }
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
        <label className="grid gap-1 text-sm">
            <span className="font-medium text-muted-foreground">{label}</span>
            {children}
        </label>
    );
}

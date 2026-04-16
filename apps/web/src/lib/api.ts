const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export type DatasetInfo = {
    key: string;
    description: string;
    filters: string[];
    requires_filter_for_download: boolean;
};

export type FiltersResponse = {
    years: number[];
    districts: string[];
    genders: string[];
    races: string[];
    ethnicities: string[];
};

export type SchoolItem = {
    school_key: number;
    school_year_start: number;
    school_year_label: string;
    dist_name: string;
    school_name: string;
};

export type PreviewResponse = {
    dataset: string;
    limit: number;
    offset: number;
    row_count: number;
    rows: Array<Record<string, unknown>>;
};

export async function fetchDatasets(): Promise<DatasetInfo[]> {
    const response = await fetch(`${API_BASE}/datasets`);
    if (!response.ok) throw new Error("Failed to load datasets");
    return response.json();
}

export async function fetchFilters(): Promise<FiltersResponse> {
    const response = await fetch(`${API_BASE}/filters`);
    if (!response.ok) throw new Error("Failed to load filters");
    return response.json();
}

export async function fetchSchools(search: {
    q?: string;
    year?: number;
    limit?: number;
    offset?: number;
}): Promise<SchoolItem[]> {
    const params = new URLSearchParams();
    if (search.q) params.set("q", search.q);
    if (search.year !== undefined) params.set("year", String(search.year));
    params.set("limit", String(search.limit ?? 200));
    params.set("offset", String(search.offset ?? 0));

    const response = await fetch(`${API_BASE}/schools?${params.toString()}`);
    if (!response.ok) throw new Error("Failed to load schools");
    return response.json();
}

export async function fetchPreview(
    dataset: string,
    search: Record<string, string | number | undefined>,
): Promise<PreviewResponse> {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(search)) {
        if (value === undefined || value === "") continue;
        params.set(key, String(value));
    }

    const response = await fetch(
        `${API_BASE}/data/${dataset}?${params.toString()}`,
    );
    if (!response.ok) {
        const body = await response
            .json()
            .catch(() => ({ detail: "Preview request failed" }));
        throw new Error(body.detail ?? "Preview request failed");
    }
    return response.json();
}

export function getDownloadUrl(
    dataset: string,
    search: Record<string, string | number | undefined>,
) {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(search)) {
        if (value === undefined || value === "") continue;
        params.set(key, String(value));
    }
    return `${API_BASE}/download/${dataset}.csv?${params.toString()}`;
}

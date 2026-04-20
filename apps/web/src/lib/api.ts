const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

function buildSearchParams(
    search: Record<string, string | number | undefined>,
) {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(search)) {
        if (value === undefined || value === "") continue;
        params.set(key, String(value));
    }
    return params;
}

async function readErrorMessage(
    response: Response,
    fallbackMessage: string,
): Promise<string> {
    const body = await response
        .json()
        .catch(() => ({ detail: fallbackMessage }));
    return body.detail ?? fallbackMessage;
}

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

export type SimulatorTarget =
    | "ach_all"
    | "per_pupil_total_raw"
    | "nces_poverty"
    | "nces_freelunch"
    | "exp_rate"
    | "inexp_rate";

export type SimulatorPayload = {
    ach_all?: number;
    per_pupil_total_raw?: number;
    nces_poverty?: number;
    nces_freelunch?: number;
    exp_rate?: number;
    inexp_rate?: number;
    nces_locale_type?: string;
    is_charter?: number;
    is_magnet?: number;
    pct_american_indian_alaska_native?: number;
    pct_asian?: number;
    pct_black_or_african_american?: number;
    pct_native_hawaiian_pacific_islander?: number;
    pct_two_or_more_races?: number;
    pct_white?: number;
};

export type BaselineResponse = Required<
    Pick<
        SimulatorPayload,
        | "ach_all"
        | "per_pupil_total_raw"
        | "nces_poverty"
        | "nces_freelunch"
        | "exp_rate"
        | "inexp_rate"
        | "nces_locale_type"
        | "is_charter"
        | "is_magnet"
        | "pct_american_indian_alaska_native"
        | "pct_asian"
        | "pct_black_or_african_american"
        | "pct_native_hawaiian_pacific_islander"
        | "pct_two_or_more_races"
        | "pct_white"
    >
>;

export type PredictionResponse = {
    target: SimulatorTarget;
    predicted_value: number;
    model_type: string;
    features_used: string[];
};

export type DistrictRankingItem = {
    district_key: number;
    district_name: string;
    year: number;
    school_count: number;
    avg_per_pupil_funding: number | null;
    avg_achievement: number | null;
    funding_rank: number;
};

export type DistrictRankingsResponse = {
    year: number;
    limit: number;
    next_cursor: string | null;
    items: DistrictRankingItem[];
};

export type DistrictSchoolItem = {
    district_key: number;
    district_name: string;
    school_key: number;
    school_name: string;
    year: number;
    per_pupil_total_raw: number | null;
    ach_all: number | null;
};

export type DistrictSchoolsResponse = {
    district_key: number;
    year: number;
    limit: number;
    next_cursor: string | null;
    items: DistrictSchoolItem[];
};

export type SchoolPerformancePoint = {
    year: number;
    per_pupil_total_raw: number | null;
    ach_all: number | null;
    grw_all: number | null;
    abs_all: number | null;
};

export type SchoolPerformanceResponse = {
    school_key: number;
    school_name: string | null;
    district_name: string | null;
    from_year: number | null;
    to_year: number | null;
    points: SchoolPerformancePoint[];
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
    const params = buildSearchParams(search);

    const response = await fetch(
        `${API_BASE}/data/${dataset}?${params.toString()}`,
    );
    if (!response.ok) {
        throw new Error(
            await readErrorMessage(response, "Preview request failed"),
        );
    }
    return response.json();
}

export async function fetchBaseline(
    schoolKey: number,
    year: number,
): Promise<BaselineResponse> {
    const response = await fetch(
        `${API_BASE}/predict/baseline/${schoolKey}/${year}`,
    );
    if (!response.ok) {
        throw new Error(
            await readErrorMessage(response, "Failed to load baseline"),
        );
    }
    return response.json();
}

export async function predictTarget(
    target: SimulatorTarget,
    payload: SimulatorPayload,
): Promise<PredictionResponse> {
    const response = await fetch(`${API_BASE}/predict/${target}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        throw new Error(
            await readErrorMessage(response, "Prediction request failed"),
        );
    }

    return response.json();
}

export async function fetchDistrictRankings(search: {
    year?: number;
    limit?: number;
    cursor?: string;
}): Promise<DistrictRankingsResponse> {
    const params = buildSearchParams({
        year: search.year,
        limit: search.limit,
        cursor: search.cursor,
    });
    const response = await fetch(
        `${API_BASE}/rankings/districts?${params.toString()}`,
    );
    if (!response.ok) {
        throw new Error(
            await readErrorMessage(
                response,
                "Failed to load district rankings",
            ),
        );
    }
    return response.json();
}

export async function fetchDistrictSchools(
    districtKey: number,
    search: {
        year?: number;
        limit?: number;
        cursor?: string;
    },
): Promise<DistrictSchoolsResponse> {
    const params = buildSearchParams({
        year: search.year,
        limit: search.limit,
        cursor: search.cursor,
    });
    const response = await fetch(
        `${API_BASE}/rankings/districts/${districtKey}/schools?${params.toString()}`,
    );
    if (!response.ok) {
        throw new Error(
            await readErrorMessage(response, "Failed to load district schools"),
        );
    }
    return response.json();
}

export async function fetchSchoolPerformanceTrend(
    schoolKey: number,
    search: {
        from_year?: number;
        to_year?: number;
    },
): Promise<SchoolPerformanceResponse> {
    const params = buildSearchParams(search);
    const response = await fetch(
        `${API_BASE}/rankings/schools/${schoolKey}/performance?${params.toString()}`,
    );
    if (!response.ok) {
        throw new Error(
            await readErrorMessage(
                response,
                "Failed to load school performance",
            ),
        );
    }
    return response.json();
}

export function getDownloadUrl(
    dataset: string,
    search: Record<string, string | number | undefined>,
) {
    const params = buildSearchParams(search);
    return `${API_BASE}/download/${dataset}.csv?${params.toString()}`;
}

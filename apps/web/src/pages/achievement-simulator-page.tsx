import { useQuery } from "@tanstack/react-query";
import { type ReactNode, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import {
    type BaselineResponse,
    fetchBaseline,
    fetchFilters,
    fetchSchoolSimulationMetadata,
    fetchSchools,
    predictTarget,
    type SchoolItem,
    type SchoolSimulationMetadataResponse,
    type SimulatorPayload,
    type SimulatorTarget,
} from "@/lib/api";

const demographicKeys = [
    "pct_american_indian_alaska_native",
    "pct_asian",
    "pct_black_or_african_american",
    "pct_native_hawaiian_pacific_islander",
    "pct_two_or_more_races",
    "pct_white",
] as const;

const METADATA_STALE_TIME_MS = 10 * 60 * 1000;
const METADATA_GC_TIME_MS = 30 * 60 * 1000;

type SchoolDistrictGroup = {
    districtName: string;
    schools: SchoolItem[];
};

export function AchievementSimulatorPage() {
    const [selectedYear, setSelectedYear] = useState<number | undefined>();
    const [schoolQuery, setSchoolQuery] = useState("");
    const [selectedSchoolKey, setSelectedSchoolKey] = useState<number | null>(null);
    const [baseline, setBaseline] = useState<BaselineResponse | null>(null);
    const [scenario, setScenario] = useState<SimulatorPayload | null>(null);
    const [dirtyFields, setDirtyFields] = useState<Record<string, boolean>>({});
    const [isRunning, setIsRunning] = useState(false);
    const [runError, setRunError] = useState<string | null>(null);

    const filtersQuery = useQuery({
        queryKey: ["filters"],
        queryFn: fetchFilters,
        staleTime: METADATA_STALE_TIME_MS,
        gcTime: METADATA_GC_TIME_MS,
    });

    useEffect(() => {
        if (!selectedYear && filtersQuery.data?.years.length) {
            const latestYear = Math.max(...filtersQuery.data.years);
            setSelectedYear(latestYear);
        }
    }, [filtersQuery.data, selectedYear]);

    const schoolsQuery = useQuery({
        queryKey: ["simulator-schools", schoolQuery, selectedYear],
        queryFn: () =>
            fetchSchools({
                q: schoolQuery || undefined,
                year: selectedYear,
                limit: 200,
                offset: 0,
            }),
        enabled: selectedYear !== undefined,
    });

    const simulationMetadataQuery = useQuery<SchoolSimulationMetadataResponse>({
        queryKey: ["school-simulation-metadata", selectedSchoolKey, selectedYear],
        queryFn: () => {
            if (!selectedSchoolKey) {
                throw new Error("School is required");
            }
            return fetchSchoolSimulationMetadata(selectedSchoolKey, {
                year: selectedYear,
            });
        },
        enabled: selectedSchoolKey !== null,
    });

    const simulationMetadata = simulationMetadataQuery.data;

    useEffect(() => {
        if (!selectedSchoolKey || selectedYear !== undefined) {
            return;
        }
        if (simulationMetadata?.selected_year != null) {
            setSelectedYear(simulationMetadata.selected_year);
        }
    }, [selectedSchoolKey, selectedYear, simulationMetadata]);

    const schoolsByDistrict = (schoolsQuery.data ?? []).reduce<SchoolDistrictGroup[]>(
        (groups, school) => {
            const districtName = school.dist_name?.trim() || "Unknown District";
            const existingGroup = groups.find(
                (group) => group.districtName === districtName,
            );

            if (existingGroup) {
                existingGroup.schools.push(school);
                return groups;
            }

            groups.push({ districtName, schools: [school] });
            return groups;
        },
        [],
    );

    const baselineQuery = useQuery({
        queryKey: ["simulator-baseline", selectedSchoolKey, selectedYear],
        queryFn: () => {
            if (!selectedSchoolKey || !selectedYear) {
                throw new Error("Missing school/year selection");
            }
            return fetchBaseline(selectedSchoolKey, selectedYear);
        },
        enabled: selectedSchoolKey !== null && selectedYear !== undefined,
        retry: false,
    });

    useEffect(() => {
        if (baselineQuery.data) {
            setBaseline(baselineQuery.data);
            setScenario(baselineQuery.data);
            setDirtyFields({});
            setRunError(null);
        }
    }, [baselineQuery.data]);

    const raceTotal = demographicKeys.reduce(
        (sum, key) => sum + Number(scenario?.[key] ?? 0),
        0,
    );

    const markDirty = (key: keyof SimulatorPayload) => {
        setDirtyFields((prev) => ({ ...prev, [key]: true }));
    };

    const updateNumericField = (key: keyof SimulatorPayload, value: number) => {
        setScenario((prev) => {
            if (!prev) {
                return prev;
            }

            const next = {
                ...prev,
                [key]: value,
            };

            if (key === "exp_rate") {
                next.inexp_rate = Math.max(0, Math.min(100, 100 - value));
                setDirtyFields((draft) => ({
                    ...draft,
                    exp_rate: true,
                    inexp_rate: true,
                }));
            } else if (key === "inexp_rate") {
                next.exp_rate = Math.max(0, Math.min(100, 100 - value));
                setDirtyFields((draft) => ({
                    ...draft,
                    exp_rate: true,
                    inexp_rate: true,
                }));
            } else {
                markDirty(key);
            }

            return next;
        });
    };

    const runSimulation = async () => {
        if (!scenario) {
            return;
        }

        setIsRunning(true);
        setRunError(null);

        const nextScenario: SimulatorPayload = { ...scenario };

        const maybePredict = async (target: SimulatorTarget) => {
            if (dirtyFields[target]) {
                return;
            }
            const result = await predictTarget(target, nextScenario);
            nextScenario[target] = result.predicted_value;
        };

        try {
            await maybePredict("per_pupil_total_raw");
            await maybePredict("nces_poverty");
            await maybePredict("nces_freelunch");
            await maybePredict("exp_rate");
            await maybePredict("inexp_rate");

            const achResult = await predictTarget("ach_all", nextScenario);
            nextScenario.ach_all = achResult.predicted_value;

            setScenario(nextScenario);
        } catch (error) {
            setRunError(error instanceof Error ? error.message : "Simulation failed");
        } finally {
            setIsRunning(false);
        }
    };

    const resetScenario = () => {
        if (!baseline) {
            return;
        }
        setScenario(baseline);
        setDirtyFields({});
        setRunError(null);
    };

    const baselineAchievement = baseline?.ach_all;
    const scenarioAchievement = scenario?.ach_all ?? baselineAchievement;
    const hasAchievementValues =
        baselineAchievement != null && scenarioAchievement != null;
    const achievementDelta = hasAchievementValues
        ? scenarioAchievement - baselineAchievement
        : null;
    const achievementPct =
        hasAchievementValues && baselineAchievement !== 0
            ? ((scenarioAchievement - baselineAchievement) / baselineAchievement) * 100
            : null;

    return (
        <section className="grid gap-4 lg:grid-cols-[340px_1fr]">
            <Card>
                <CardHeader>
                    <CardTitle>School Baseline</CardTitle>
                    <CardDescription>
                        Select a school/year and load baseline model inputs.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                    <Field label="Year">
                        <Select
                            value={selectedYear?.toString() ?? ""}
                            onChange={(event) => {
                                const next = event.target.value
                                    ? Number(event.target.value)
                                    : undefined;
                                setSelectedYear(next);
                                setSelectedSchoolKey(null);
                                setBaseline(null);
                                setScenario(null);
                            }}
                        >
                            <option value="">Select year</option>
                            {(
                                simulationMetadata?.available_years ??
                                filtersQuery.data?.years ??
                                []
                            ).map((year) => (
                                <option key={year} value={year}>
                                    {year}
                                </option>
                            ))}
                        </Select>
                    </Field>

                    <Field label="School search">
                        <Input
                            value={schoolQuery}
                            placeholder="Type district or school"
                            onChange={(event) => setSchoolQuery(event.target.value)}
                        />
                    </Field>

                    <Field label="School">
                        <Select
                            value={selectedSchoolKey?.toString() ?? ""}
                            onChange={(event) => {
                                setSelectedSchoolKey(
                                    event.target.value
                                        ? Number(event.target.value)
                                        : null,
                                );
                                setSelectedYear(undefined);
                                setBaseline(null);
                                setScenario(null);
                                setRunError(null);
                            }}
                        >
                            <option value="">Select school</option>
                            {schoolsByDistrict.map((group) => (
                                <optgroup
                                    key={group.districtName}
                                    label={group.districtName}
                                >
                                    {group.schools.map((school) => (
                                        <option
                                            key={`${school.school_key}-${school.school_year_start}`}
                                            value={school.school_key}
                                        >
                                            {school.school_name}
                                        </option>
                                    ))}
                                </optgroup>
                            ))}
                        </Select>
                    </Field>

                    {baselineQuery.isFetching && (
                        <p className="text-xs text-muted-foreground">
                            Loading baseline...
                        </p>
                    )}
                    {baselineQuery.error instanceof Error && (
                        <p className="text-xs text-red-600">
                            {baselineQuery.error.message}
                        </p>
                    )}

                    {baseline && (
                        <div className="rounded-md border bg-muted/40 p-3 text-xs text-muted-foreground">
                            <p>Locale: {baseline.nces_locale_type}</p>
                            <p>Charter: {baseline.is_charter ? "Yes" : "No"}</p>
                            <p>Magnet: {baseline.is_magnet ? "Yes" : "No"}</p>
                            <p>
                                Latest simulatable year:{" "}
                                {simulationMetadata?.latest_simulatable_year ?? "-"}
                            </p>
                        </div>
                    )}

                    {simulationMetadata && !simulationMetadata.is_simulatable && (
                        <p className="text-xs text-amber-700">
                            Selected year is not simulatable. Missing fields:{" "}
                            {simulationMetadata.missing_features.join(", ") || "Unknown"}
                        </p>
                    )}
                </CardContent>
            </Card>

            <div className="space-y-4">
                <Card>
                    <CardHeader>
                        <CardTitle>Scenario Controls</CardTitle>
                        <CardDescription>
                            Adjust policy-sensitive inputs, then run simulation.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="grid gap-4 md:grid-cols-2">
                        <RangeField
                            label="Per pupil funding"
                            min={4000}
                            max={30000}
                            step={100}
                            value={Number(scenario?.per_pupil_total_raw ?? 0)}
                            suffix="$"
                            onChange={(value) =>
                                updateNumericField("per_pupil_total_raw", value)
                            }
                        />
                        <RangeField
                            label="Poverty rate"
                            min={0}
                            max={100}
                            step={1}
                            value={Number(scenario?.nces_poverty ?? 0) * 100}
                            suffix="%"
                            onChange={(value) =>
                                updateNumericField("nces_poverty", value / 100)
                            }
                        />
                        <RangeField
                            label="Free lunch count"
                            min={0}
                            max={2500}
                            step={1}
                            value={Number(scenario?.nces_freelunch ?? 0)}
                            onChange={(value) =>
                                updateNumericField("nces_freelunch", value)
                            }
                        />
                        <RangeField
                            label="Experienced teacher rate"
                            min={0}
                            max={100}
                            step={0.5}
                            value={Number(scenario?.exp_rate ?? 0)}
                            suffix="%"
                            onChange={(value) => updateNumericField("exp_rate", value)}
                        />

                        {demographicKeys.map((key) => (
                            <RangeField
                                key={key}
                                label={key
                                    .replace("pct_", "")
                                    .replaceAll("_", " ")
                                    .replace(/\b\w/g, (match) => match.toUpperCase())}
                                min={0}
                                max={100}
                                step={1}
                                value={Number(scenario?.[key] ?? 0) * 100}
                                suffix="%"
                                onChange={(value) => updateNumericField(key, value / 100)}
                            />
                        ))}
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle>Outcome Snapshot</CardTitle>
                        <CardDescription>
                            Baseline vs scenario prediction for achievement.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                        <div className="grid gap-2 md:grid-cols-3">
                            <Metric
                                label="Baseline Achievement"
                                value={
                                    baselineAchievement != null
                                        ? baselineAchievement.toFixed(2)
                                        : "--"
                                }
                            />
                            <Metric
                                label="Scenario Achievement"
                                value={
                                    scenarioAchievement != null
                                        ? scenarioAchievement.toFixed(2)
                                        : "--"
                                }
                            />
                            <Metric
                                label="Delta"
                                value={
                                    achievementDelta != null && achievementPct != null
                                        ? `${achievementDelta >= 0 ? "+" : ""}${achievementDelta.toFixed(2)} (${achievementPct.toFixed(1)}%)`
                                        : "--"
                                }
                            />
                        </div>
                        <p className="text-xs text-muted-foreground">
                            Race percentage total: {(raceTotal * 100).toFixed(1)}%
                            {raceTotal > 1 && " (above 100% - adjust for realism)"}
                        </p>
                        {runError && <p className="text-sm text-red-600">{runError}</p>}
                        <div className="flex gap-2">
                            <Button
                                onClick={runSimulation}
                                disabled={
                                    !scenario ||
                                    isRunning ||
                                    (simulationMetadata
                                        ? !simulationMetadata.is_simulatable
                                        : false)
                                }
                            >
                                {isRunning ? "Running..." : "Run Simulation"}
                            </Button>
                            <Button
                                variant="outline"
                                onClick={resetScenario}
                                disabled={!baseline || isRunning}
                            >
                                Reset to Baseline
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </section>
    );
}

function RangeField({
    label,
    value,
    min,
    max,
    step,
    suffix,
    onChange,
}: {
    label: string;
    value: number;
    min: number;
    max: number;
    step: number;
    suffix?: string;
    onChange: (value: number) => void;
}) {
    return (
        <div className="space-y-1">
            <label className="text-sm font-medium text-muted-foreground">{label}</label>
            <Input
                type="range"
                min={min}
                max={max}
                step={step}
                value={Number.isFinite(value) ? value : 0}
                onChange={(event) => onChange(Number(event.target.value))}
            />
            <p className="text-xs text-muted-foreground">
                {value.toFixed(2)}
                {suffix ? ` ${suffix}` : ""}
            </p>
        </div>
    );
}

function Metric({ label, value }: { label: string; value: string }) {
    return (
        <div className="rounded-md border bg-muted/30 p-3">
            <p className="text-xs text-muted-foreground">{label}</p>
            <p className="text-lg font-semibold">{value}</p>
        </div>
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

import { useQuery } from "@tanstack/react-query";
import { type ReactNode, useEffect, useMemo, useState } from "react";

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
    fetchSchoolSimulationMetadata,
    fetchSchools,
    predictTarget,
    type SchoolItem,
    type SchoolSimulationMetadataResponse,
    type SimulatorPayload,
} from "@/lib/api";

const demographicKeys = [
    "pct_american_indian_alaska_native",
    "pct_asian",
    "pct_black_or_african_american",
    "pct_native_hawaiian_pacific_islander",
    "pct_two_or_more_races",
    "pct_white",
] as const;

type AdjustableField =
    | "per_pupil_total_raw"
    | "nces_poverty"
    | "nces_freelunch"
    | "exp_rate"
    | "inexp_rate"
    | (typeof demographicKeys)[number];

const TEACHER_EXPERIENCE_GROUP = "teacher_experience";

function toGroupKey(field: AdjustableField) {
    if (field === "exp_rate" || field === "inexp_rate") {
        return TEACHER_EXPERIENCE_GROUP;
    }
    return field;
}

function useSchoolYearMetadata(
    schoolKey: number | null,
    selectedYear: number | undefined,
) {
    return useQuery({
        queryKey: ["school-simulation-metadata", schoolKey, selectedYear],
        queryFn: () => {
            if (schoolKey === null) {
                throw new Error("School is required");
            }
            return fetchSchoolSimulationMetadata(schoolKey, { year: selectedYear });
        },
        enabled: schoolKey !== null,
    });
}

function useSingleVariableScenario(baseline: BaselineResponse | null) {
    const [scenario, setScenario] = useState<SimulatorPayload | null>(baseline);
    const [activeGroup, setActiveGroup] = useState<string | null>(null);

    useEffect(() => {
        setScenario(baseline);
        setActiveGroup(null);
    }, [baseline]);

    const updateField = (field: AdjustableField, value: number) => {
        const targetGroup = toGroupKey(field);
        if (activeGroup && activeGroup !== targetGroup) {
            return;
        }

        setActiveGroup(targetGroup);
        setScenario((prev) => {
            if (!prev) {
                return prev;
            }

            if (field === "exp_rate") {
                return {
                    ...prev,
                    exp_rate: value,
                    inexp_rate: Math.max(0, Math.min(100, 100 - value)),
                };
            }

            if (field === "inexp_rate") {
                return {
                    ...prev,
                    inexp_rate: value,
                    exp_rate: Math.max(0, Math.min(100, 100 - value)),
                };
            }

            return {
                ...prev,
                [field]: value,
            };
        });
    };

    const resetScenario = () => {
        setScenario(baseline);
        setActiveGroup(null);
    };

    const isLocked = (field: AdjustableField) => {
        const targetGroup = toGroupKey(field);
        return Boolean(activeGroup && activeGroup !== targetGroup);
    };

    return {
        activeGroup,
        isLocked,
        resetScenario,
        scenario,
        setScenario,
        updateField,
    };
}

export function AchievementSimulatorView() {
    const [selectedYear, setSelectedYear] = useState<number | undefined>();
    const [schoolQuery, setSchoolQuery] = useState("");
    const [selectedSchoolKey, setSelectedSchoolKey] = useState<number | null>(null);
    const [isRunning, setIsRunning] = useState(false);
    const [runError, setRunError] = useState<string | null>(null);
    const [showMetadata, setShowMetadata] = useState(false);

    const schoolsQuery = useQuery({
        queryKey: ["simulator-schools", schoolQuery],
        queryFn: () =>
            fetchSchools({
                q: schoolQuery || undefined,
                limit: 200,
                offset: 0,
            }),
    });

    const schoolOptions = useMemo(() => {
        const latestBySchool = new Map<number, SchoolItem>();
        for (const school of schoolsQuery.data ?? []) {
            const existing = latestBySchool.get(school.school_key);
            if (!existing || school.school_year_start > existing.school_year_start) {
                latestBySchool.set(school.school_key, school);
            }
        }
        return Array.from(latestBySchool.values()).sort((a, b) => {
            if (a.dist_name === b.dist_name) {
                return a.school_name.localeCompare(b.school_name);
            }
            return a.dist_name.localeCompare(b.dist_name);
        });
    }, [schoolsQuery.data]);

    const metadataQuery = useSchoolYearMetadata(selectedSchoolKey, selectedYear);
    const metadata = metadataQuery.data;

    useEffect(() => {
        if (!metadata?.selected_year) {
            return;
        }
        if (selectedYear !== metadata.selected_year) {
            setSelectedYear(metadata.selected_year);
        }
    }, [metadata, selectedYear]);

    const baselineQuery = useQuery({
        queryKey: ["simulator-baseline", selectedSchoolKey, selectedYear],
        queryFn: () => {
            if (selectedSchoolKey === null || selectedYear === undefined) {
                throw new Error("Select a school and year");
            }
            return fetchBaseline(selectedSchoolKey, selectedYear);
        },
        enabled: selectedSchoolKey !== null && selectedYear !== undefined,
        retry: false,
    });

    const baseline = baselineQuery.data ?? null;
    const { activeGroup, isLocked, resetScenario, scenario, setScenario, updateField } =
        useSingleVariableScenario(baseline);

    const baselineReady =
        Boolean(scenario) && !baselineQuery.isLoading && !baselineQuery.error;

    const raceTotal = demographicKeys.reduce(
        (sum, key) => sum + Number(scenario?.[key] ?? 0),
        0,
    );

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

    const runSimulation = async () => {
        if (!scenario) {
            return;
        }

        setIsRunning(true);
        setRunError(null);

        try {
            const result = await predictTarget("ach_all", scenario);
            setScenario((prev) =>
                prev
                    ? {
                          ...prev,
                          ach_all: result.predicted_value,
                      }
                    : prev,
            );
        } catch (error) {
            setRunError(error instanceof Error ? error.message : "Simulation failed");
        } finally {
            setIsRunning(false);
        }
    };

    const selectedSchool = schoolOptions.find(
        (option) => option.school_key === selectedSchoolKey,
    );

    return (
        <section className="grid gap-4 lg:grid-cols-[340px_1fr]">
            <SchoolSelectionCard
                metadata={metadata}
                metadataError={metadataQuery.error}
                schoolOptions={schoolOptions}
                schoolQuery={schoolQuery}
                selectedSchool={selectedSchool}
                selectedSchoolKey={selectedSchoolKey}
                selectedYear={selectedYear}
                setSchoolQuery={setSchoolQuery}
                setSelectedSchoolKey={(schoolKey) => {
                    setSelectedSchoolKey(schoolKey);
                    setSelectedYear(undefined);
                    setRunError(null);
                }}
                setSelectedYear={setSelectedYear}
                showMetadata={() => setShowMetadata(true)}
            />

            <div className="space-y-4">
                <ScenarioControlsCard
                    activeGroup={activeGroup}
                    isLocked={isLocked}
                    scenarioReady={baselineReady}
                    scenario={scenario}
                    updateField={updateField}
                />

                <OutcomeSnapshotCard
                    achievementDelta={achievementDelta}
                    achievementPct={achievementPct}
                    baselineAchievement={baselineAchievement}
                    baselineError={
                        baselineQuery.error instanceof Error
                            ? baselineQuery.error.message
                            : null
                    }
                    baselineLoading={baselineQuery.isLoading}
                    canRun={Boolean(
                        scenario && metadata?.is_simulatable && baselineReady,
                    )}
                    isRunning={isRunning}
                    metadata={metadata}
                    raceTotal={raceTotal}
                    resetScenario={resetScenario}
                    runError={runError}
                    runSimulation={runSimulation}
                    scenarioAchievement={scenarioAchievement}
                />
            </div>

            {showMetadata && (
                <SchoolMetadataPopup
                    metadata={metadata}
                    onClose={() => setShowMetadata(false)}
                />
            )}
        </section>
    );
}

function SchoolSelectionCard({
    metadata,
    metadataError,
    schoolOptions,
    schoolQuery,
    selectedSchool,
    selectedSchoolKey,
    selectedYear,
    setSchoolQuery,
    setSelectedSchoolKey,
    setSelectedYear,
    showMetadata,
}: {
    metadata: SchoolSimulationMetadataResponse | undefined;
    metadataError: unknown;
    schoolOptions: Array<{
        school_key: number;
        school_name: string;
        dist_name: string;
    }>;
    schoolQuery: string;
    selectedSchool:
        | {
              school_key: number;
              school_name: string;
              dist_name: string;
          }
        | undefined;
    selectedSchoolKey: number | null;
    selectedYear: number | undefined;
    setSchoolQuery: (value: string) => void;
    setSelectedSchoolKey: (value: number | null) => void;
    setSelectedYear: (value: number | undefined) => void;
    showMetadata: () => void;
}) {
    return (
        <Card>
            <CardHeader>
                <CardTitle>School Baseline</CardTitle>
                <CardDescription>
                    Select a school and the view defaults to its latest simulatable year.
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
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
                        onChange={(event) =>
                            setSelectedSchoolKey(
                                event.target.value ? Number(event.target.value) : null,
                            )
                        }
                    >
                        <option value="">Select school</option>
                        {schoolOptions.map((school) => (
                            <option key={school.school_key} value={school.school_key}>
                                {school.school_name} - {school.dist_name}
                            </option>
                        ))}
                    </Select>
                </Field>

                <Field label="Year">
                    <Select
                        value={selectedYear?.toString() ?? ""}
                        onChange={(event) =>
                            setSelectedYear(
                                event.target.value
                                    ? Number(event.target.value)
                                    : undefined,
                            )
                        }
                        disabled={!selectedSchoolKey}
                    >
                        <option value="">Select year</option>
                        {metadata?.available_years.map((year) => (
                            <option key={year} value={year}>
                                {year}
                            </option>
                        ))}
                    </Select>
                </Field>

                {selectedSchool && (
                    <div className="rounded-md border bg-muted/40 p-3 text-xs text-muted-foreground">
                        <p>{selectedSchool.school_name}</p>
                        <p>{selectedSchool.dist_name}</p>
                        <p>
                            Latest simulatable year:{" "}
                            {metadata?.latest_simulatable_year ?? "-"}
                        </p>
                    </div>
                )}

                {metadataError instanceof Error && (
                    <p className="text-xs text-red-600">{metadataError.message}</p>
                )}

                <Button variant="outline" onClick={showMetadata} disabled={!metadata}>
                    View Data Metadata
                </Button>
            </CardContent>
        </Card>
    );
}

function ScenarioControlsCard({
    activeGroup,
    isLocked,
    scenarioReady,
    scenario,
    updateField,
}: {
    activeGroup: string | null;
    isLocked: (field: AdjustableField) => boolean;
    scenarioReady: boolean;
    scenario: SimulatorPayload | null;
    updateField: (field: AdjustableField, value: number) => void;
}) {
    return (
        <Card>
            <CardHeader>
                <CardTitle>Scenario Controls</CardTitle>
                <CardDescription>
                    Change one variable group at a time. Teacher experience rates are
                    mutually exclusive and update together.
                </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
                <RangeField
                    label="Per pupil funding"
                    min={4000}
                    max={30000}
                    step={100}
                    suffix="$"
                    value={Number(scenario?.per_pupil_total_raw ?? 0)}
                    onChange={(value) => updateField("per_pupil_total_raw", value)}
                    disabled={!scenarioReady || isLocked("per_pupil_total_raw")}
                />
                <RangeField
                    label="Poverty rate"
                    min={0}
                    max={100}
                    step={1}
                    suffix="%"
                    value={Number(scenario?.nces_poverty ?? 0) * 100}
                    onChange={(value) => updateField("nces_poverty", value / 100)}
                    disabled={!scenarioReady || isLocked("nces_poverty")}
                />
                <RangeField
                    label="Free lunch count"
                    min={0}
                    max={2500}
                    step={1}
                    value={Number(scenario?.nces_freelunch ?? 0)}
                    onChange={(value) => updateField("nces_freelunch", value)}
                    disabled={!scenarioReady || isLocked("nces_freelunch")}
                />
                <RangeField
                    label="Experienced teacher rate"
                    min={0}
                    max={100}
                    step={0.5}
                    suffix="%"
                    value={Number(scenario?.exp_rate ?? 0)}
                    onChange={(value) => updateField("exp_rate", value)}
                    disabled={!scenarioReady || isLocked("exp_rate")}
                />
                <RangeField
                    label="Inexperienced teacher rate"
                    min={0}
                    max={100}
                    step={0.5}
                    suffix="%"
                    value={Number(scenario?.inexp_rate ?? 0)}
                    onChange={(value) => updateField("inexp_rate", value)}
                    disabled={!scenarioReady || isLocked("inexp_rate")}
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
                        suffix="%"
                        value={Number(scenario?.[key] ?? 0) * 100}
                        onChange={(value) => updateField(key, value / 100)}
                        disabled={!scenarioReady || isLocked(key)}
                    />
                ))}
                {activeGroup && (
                    <p className="text-xs text-muted-foreground md:col-span-2">
                        Active variable group: {activeGroup}
                    </p>
                )}
            </CardContent>
        </Card>
    );
}

function OutcomeSnapshotCard({
    achievementDelta,
    achievementPct,
    baselineError,
    baselineLoading,
    baselineAchievement,
    canRun,
    isRunning,
    metadata,
    raceTotal,
    resetScenario,
    runError,
    runSimulation,
    scenarioAchievement,
}: {
    achievementDelta: number | null;
    achievementPct: number | null;
    baselineError: string | null;
    baselineLoading: boolean;
    baselineAchievement: number | null | undefined;
    canRun: boolean;
    isRunning: boolean;
    metadata: SchoolSimulationMetadataResponse | undefined;
    raceTotal: number;
    resetScenario: () => void;
    runError: string | null;
    runSimulation: () => void;
    scenarioAchievement: number | null | undefined;
}) {
    return (
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

                {baselineLoading && (
                    <p className="text-xs text-muted-foreground">
                        Loading baseline data...
                    </p>
                )}

                {baselineError && <p className="text-xs text-red-600">{baselineError}</p>}

                {metadata && !metadata.is_simulatable && (
                    <p className="text-xs text-amber-700">
                        Missing required model fields for this school-year:{" "}
                        {metadata.missing_features.join(", ") || "Unknown fields"}
                    </p>
                )}

                {runError && <p className="text-sm text-red-600">{runError}</p>}

                <div className="flex gap-2">
                    <Button onClick={runSimulation} disabled={!canRun || isRunning}>
                        {isRunning ? "Running..." : "Run Simulation"}
                    </Button>
                    <Button
                        variant="outline"
                        onClick={resetScenario}
                        disabled={isRunning}
                    >
                        Reset to Baseline
                    </Button>
                </div>
            </CardContent>
        </Card>
    );
}

function SchoolMetadataPopup({
    metadata,
    onClose,
}: {
    metadata: SchoolSimulationMetadataResponse | undefined;
    onClose: () => void;
}) {
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
            <Card className="w-full max-w-lg">
                <CardHeader>
                    <CardTitle>School Data Metadata</CardTitle>
                    <CardDescription>
                        Summary of available years and model readiness.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                    <p>Latest year: {metadata?.latest_year ?? "-"}</p>
                    <p>
                        Latest simulatable year:{" "}
                        {metadata?.latest_simulatable_year ?? "-"}
                    </p>
                    <p>Selected year: {metadata?.selected_year ?? "-"}</p>
                    <p>Simulatable: {metadata?.is_simulatable ? "Yes" : "No"}</p>
                    <p>
                        Available years: {metadata?.available_years.join(", ") || "None"}
                    </p>
                    {!metadata?.is_simulatable && metadata && (
                        <p>
                            Missing required fields:{" "}
                            {metadata.missing_features.join(", ")}
                        </p>
                    )}
                    {metadata?.year_status?.length ? (
                        <div className="space-y-1 pt-2 text-xs">
                            {metadata.year_status.map((status) => (
                                <p key={status.year}>
                                    {status.year}:{" "}
                                    {status.is_simulatable ? "Ready" : "Missing data"}
                                </p>
                            ))}
                        </div>
                    ) : null}
                    <Button variant="outline" onClick={onClose}>
                        Close
                    </Button>
                </CardContent>
            </Card>
        </div>
    );
}

function RangeField({
    disabled,
    label,
    max,
    min,
    onChange,
    step,
    suffix,
    value,
}: {
    disabled?: boolean;
    label: string;
    max: number;
    min: number;
    onChange: (value: number) => void;
    step: number;
    suffix?: string;
    value: number;
}) {
    return (
        <div className="space-y-1">
            <label className="text-sm font-medium text-muted-foreground">{label}</label>
            <Input
                disabled={disabled}
                max={max}
                min={min}
                onChange={(event) => onChange(Number(event.target.value))}
                step={step}
                type="range"
                value={Number.isFinite(value) ? value : 0}
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

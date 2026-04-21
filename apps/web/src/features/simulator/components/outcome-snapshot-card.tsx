import { Button } from "@/components/ui/button";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";

import { Metric } from "./shared";

type OutcomeSnapshotCardProps = {
    achievementDelta: number | null;
    achievementPct: number | null;
    baselineAchievement: number | null | undefined;
    baselineError: string | null;
    baselineLoading: boolean;
    canRun: boolean;
    isRunning: boolean;
    raceTotal: number;
    resetScenario: () => void;
    runError: string | null;
    runSimulation: () => void;
    scenarioAchievement: number | null | undefined;
};

function formatMetricValue(value: number | null | undefined) {
    return value != null ? value.toFixed(2) : "--";
}

function formatDeltaValue(
    achievementDelta: number | null,
    achievementPct: number | null,
) {
    if (achievementDelta == null || achievementPct == null) {
        return "--";
    }
    const sign = achievementDelta >= 0 ? "+" : "";
    return `${sign}${achievementDelta.toFixed(2)} (${achievementPct.toFixed(1)}%)`;
}

export function OutcomeSnapshotCard({
    achievementDelta,
    achievementPct,
    baselineAchievement,
    baselineError,
    baselineLoading,
    canRun,
    isRunning,
    raceTotal,
    resetScenario,
    runError,
    runSimulation,
    scenarioAchievement,
}: OutcomeSnapshotCardProps) {
    const baselineValue = formatMetricValue(baselineAchievement);
    const scenarioValue = formatMetricValue(scenarioAchievement);
    const deltaValue = formatDeltaValue(achievementDelta, achievementPct);
    const raceTotalLabel =
        raceTotal > 1
            ? `${(raceTotal * 100).toFixed(1)}% (above 100% - adjust for realism)`
            : `${(raceTotal * 100).toFixed(1)}%`;

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
                    <Metric label="Baseline Achievement" value={baselineValue} />
                    <Metric label="Scenario Achievement" value={scenarioValue} />
                    <Metric label="Delta" value={deltaValue} />
                </div>

                <p className="text-xs text-muted-foreground">
                    Race percentage total: {raceTotalLabel}
                </p>

                {baselineLoading && (
                    <p className="text-xs text-muted-foreground">Loading baseline...</p>
                )}
                {baselineError && <p className="text-xs text-red-600">{baselineError}</p>}
                {runError && <p className="text-sm text-red-600">{runError}</p>}

                <div className="flex gap-2">
                    <Button disabled={!canRun || isRunning} onClick={runSimulation}>
                        {isRunning ? "Running..." : "Run Simulation"}
                    </Button>
                    <Button
                        disabled={baselineAchievement == null || isRunning}
                        onClick={resetScenario}
                        variant="outline"
                    >
                        Reset to Baseline
                    </Button>
                </div>
            </CardContent>
        </Card>
    );
}

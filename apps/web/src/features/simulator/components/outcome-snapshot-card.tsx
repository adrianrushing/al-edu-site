import { Button } from '@/components/ui/button';
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from '@/components/ui/card';

import { Metric } from './shared';

const PERCENT_SCALE = 100;

type OutcomeSnapshotCardProps = {
	achievementDelta: number | null;
	achievementPct: number | null;
	baselineAchievement: number | null | undefined;
	baselineError: string | null;
	baselineLoading: boolean;
	disabledReason: string | null;
	isRunning: boolean;
	raceTotal: number;
	resetScenario: () => void;
	runError: string | null;
	scenarioAchievement: number | null | undefined;
};

function formatMetricValue(value: number | null | undefined) {
	return value != null ? value.toFixed(2) : '--';
}

function formatDeltaValue(
	achievementDelta: number | null,
	achievementPct: number | null,
) {
	if (achievementDelta == null || achievementPct == null) {
		return '--';
	}
	const sign = achievementDelta >= 0 ? '+' : '';
	return `${sign}${achievementDelta.toFixed(2)} (${achievementPct.toFixed(1)}%)`;
}

export function OutcomeSnapshotCard({
	achievementDelta,
	achievementPct,
	baselineAchievement,
	baselineError,
	baselineLoading,
	disabledReason,
	isRunning,
	raceTotal,
	resetScenario,
	runError,
	scenarioAchievement,
}: OutcomeSnapshotCardProps) {
	const baselineValue = formatMetricValue(baselineAchievement);
	const scenarioValue = formatMetricValue(scenarioAchievement);
	const deltaValue = formatDeltaValue(achievementDelta, achievementPct);

	return (
		<Card>
			<CardHeader>
				<CardTitle>3. Predicted Achievement</CardTitle>
				<CardDescription>
					Review projected change from your latest slider adjustment.
				</CardDescription>
			</CardHeader>
			<CardContent className="space-y-4">
				<div className="rounded-lg border bg-muted/20 p-4">
					<p className="text-xs uppercase tracking-wide text-muted-foreground">
						Predicted ach_all
					</p>
					<p className="text-4xl font-semibold">{scenarioValue}</p>
					<p className="mt-1 inline-flex rounded-full border px-2 py-0.5 text-xs">
						Delta {deltaValue}
					</p>
					<p className="mt-2 text-xs text-muted-foreground">
						Baseline: {baselineValue}
					</p>
				</div>

				<div className="grid gap-2 md:grid-cols-2">
					<Metric label="Delta" value={deltaValue} />
					<Metric
						label="Race percentage total"
						value={`${(raceTotal * PERCENT_SCALE).toFixed(1)}%`}
					/>
				</div>

				{baselineLoading && (
					<p className="text-xs text-muted-foreground">
						Loading baseline...
					</p>
				)}
				{baselineError && (
					<p className="text-xs text-red-600">{baselineError}</p>
				)}
				{disabledReason && (
					<p className="text-xs text-amber-700">
						Run disabled: {disabledReason}
					</p>
				)}
				{isRunning && (
					<p className="text-xs text-muted-foreground">
						Updating prediction...
					</p>
				)}
				{runError && <p className="text-sm text-red-600">{runError}</p>}

				<Button
					disabled={baselineAchievement == null || isRunning}
					onClick={resetScenario}
					variant="outline"
				>
					Reset
				</Button>
			</CardContent>
		</Card>
	);
}

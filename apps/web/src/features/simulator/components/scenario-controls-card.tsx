import { Button } from '@/components/ui/button';
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from '@/components/ui/card';
import type { SimulatorPayload } from '@/lib/api';

import {
	type AdjustableField,
	demographicKeys,
	formatDemographicLabel,
} from '../constants';
import { RangeField } from './shared';

type ScenarioControlsCardProps = {
	activeGroup: string | null;
	commitScenario: () => void;
	controlsDisabled: boolean;
	isLocked: (field: AdjustableField) => boolean;
	scenario: SimulatorPayload | null;
	unlockControls: () => void;
	updateNumericField: (key: AdjustableField, value: number) => void;
};

function GroupHeader({ title }: { title: string }) {
	return (
		<p className="mt-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground md:col-span-2">
			{title}
		</p>
	);
}

function disabledFor(
	controlsDisabled: boolean,
	isLocked: (field: AdjustableField) => boolean,
	field: AdjustableField,
) {
	return controlsDisabled || isLocked(field);
}

export function ScenarioControlsCard({
	activeGroup,
	commitScenario,
	controlsDisabled,
	isLocked,
	scenario,
	unlockControls,
	updateNumericField,
}: ScenarioControlsCardProps) {
	return (
		<Card>
			<CardHeader>
				<CardTitle>2. Scenario Lever</CardTitle>
				<CardDescription>
					One variable group can be edited at a time.
				</CardDescription>
			</CardHeader>
			<CardContent className="grid gap-4 md:grid-cols-2">
				<div className="rounded-md border bg-muted/20 p-3 text-xs text-muted-foreground md:col-span-2">
					<p>Active group: {activeGroup ?? 'None'}</p>
					<p>Teacher experience rates stay linked as complements.</p>
				</div>

				<GroupHeader title="Funding and Poverty" />
				<RangeField
					disabled={disabledFor(
						controlsDisabled,
						isLocked,
						'per_pupil_total_raw',
					)}
					label="Per pupil funding"
					max={30000}
					min={4000}
					onChange={(value) =>
						updateNumericField('per_pupil_total_raw', value)
					}
					onCommit={commitScenario}
					step={100}
					suffix="$"
					value={Number(scenario?.per_pupil_total_raw ?? 0)}
				/>
				<RangeField
					disabled={disabledFor(
						controlsDisabled,
						isLocked,
						'nces_poverty',
					)}
					label="Poverty rate"
					max={100}
					min={0}
					onChange={(value) =>
						updateNumericField('nces_poverty', value / 100)
					}
					onCommit={commitScenario}
					step={1}
					suffix="%"
					value={Number(scenario?.nces_poverty ?? 0) * 100}
				/>
				<RangeField
					disabled={disabledFor(
						controlsDisabled,
						isLocked,
						'nces_freelunch',
					)}
					label="Free lunch count"
					max={2500}
					min={0}
					onChange={(value) =>
						updateNumericField('nces_freelunch', value)
					}
					onCommit={commitScenario}
					step={1}
					value={Number(scenario?.nces_freelunch ?? 0)}
				/>

				<GroupHeader title="Teacher Experience" />
				<RangeField
					disabled={disabledFor(
						controlsDisabled,
						isLocked,
						'exp_rate',
					)}
					label="Experienced teacher rate"
					max={100}
					min={0}
					onChange={(value) => updateNumericField('exp_rate', value)}
					onCommit={commitScenario}
					step={0.5}
					suffix="%"
					value={Number(scenario?.exp_rate ?? 0)}
				/>
				<RangeField
					disabled={disabledFor(
						controlsDisabled,
						isLocked,
						'inexp_rate',
					)}
					label="Inexperienced teacher rate"
					max={100}
					min={0}
					onChange={(value) =>
						updateNumericField('inexp_rate', value)
					}
					onCommit={commitScenario}
					step={0.5}
					suffix="%"
					value={Number(scenario?.inexp_rate ?? 0)}
				/>

				<GroupHeader title="Student Demographics" />
				{demographicKeys.map((key) => (
					<RangeField
						disabled={disabledFor(controlsDisabled, isLocked, key)}
						key={key}
						label={formatDemographicLabel(key)}
						max={100}
						min={0}
						onChange={(value) =>
							updateNumericField(key, value / 100)
						}
						onCommit={commitScenario}
						step={1}
						suffix="%"
						value={Number(scenario?.[key] ?? 0) * 100}
					/>
				))}

				<div className="flex gap-2 md:col-span-2">
					<Button
						disabled={activeGroup == null}
						onClick={unlockControls}
						variant="outline"
					>
						Unlock controls
					</Button>
				</div>
			</CardContent>
		</Card>
	);
}

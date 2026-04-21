import { Button } from '@/components/ui/button';

import { DemoProfilesCard } from './components/demo-profiles-card';
import { OutcomeSnapshotCard } from './components/outcome-snapshot-card';
import { ScenarioControlsCard } from './components/scenario-controls-card';
import { SchoolMetadataPopup } from './components/school-metadata-popup';
import { SchoolSelectionCard } from './components/school-selection-card';
import { DEMO_PROFILES } from './demo-profiles';
import { useSimulatorScenario } from './use-simulator-scenario';
import { useSimulatorSelection } from './use-simulator-selection';

type HeaderProps = {
	isDemoMode: boolean;
	statusClassName: string;
	statusLabel: string;
	switchToDemo: () => void;
	switchToSchool: () => void;
};

function Header({
	isDemoMode,
	statusClassName,
	statusLabel,
	switchToDemo,
	switchToSchool,
}: HeaderProps) {
	return (
		<header className="rounded-lg border bg-gradient-to-r from-slate-50 via-white to-slate-50 p-4">
			<div className="flex items-start justify-between gap-3">
				<div>
					<h1 className="text-2xl font-semibold">
						Achievement Simulator
					</h1>
					<p className="text-sm text-muted-foreground">
						Model-based projection from school baseline and a single
						scenario lever.
					</p>
					<div className="mt-3 inline-flex rounded-md border bg-background p-1">
						<Button
							onClick={switchToDemo}
							size="sm"
							variant={isDemoMode ? 'default' : 'ghost'}
						>
							Demo Profiles
						</Button>
						<Button
							onClick={switchToSchool}
							size="sm"
							variant={!isDemoMode ? 'default' : 'ghost'}
						>
							Real School Data
						</Button>
					</div>
				</div>
				<span
					className={`inline-flex items-center justify-center rounded-md border px-4 py-2 text-sm font-medium ${statusClassName}`}
				>
					{statusLabel}
				</span>
			</div>
		</header>
	);
}

function statusChip(args: {
	hasSchool: boolean;
	isDemoMode: boolean;
	isFetchingBaseline: boolean;
	hasMetadata: boolean;
	isSimulatable: boolean;
}) {
	if (args.isDemoMode) {
		return {
			label: 'Ready to simulate',
			className: 'border-emerald-300 bg-emerald-50 text-emerald-700',
		};
	}
	if (!args.hasSchool) {
		return {
			label: 'Select school',
			className: 'border-slate-300 bg-slate-50 text-slate-700',
		};
	}
	if (args.isFetchingBaseline) {
		return {
			label: 'Loading baseline',
			className: 'border-slate-300 bg-slate-50 text-slate-700',
		};
	}
	if (args.hasMetadata && !args.isSimulatable) {
		return {
			label: 'Data incomplete',
			className: 'border-amber-300 bg-amber-50 text-amber-700',
		};
	}
	return {
		label: 'Ready to simulate',
		className: 'border-emerald-300 bg-emerald-50 text-emerald-700',
	};
}

function disabledReason(args: {
	hasScenario: boolean;
	isBaselineReady: boolean;
	hasMetadata: boolean;
	isSimulatable: boolean;
}) {
	if (!args.hasScenario) return 'select a school and year';
	if (!args.isBaselineReady) return 'baseline data is still loading';
	if (!args.hasMetadata) return 'metadata is loading';
	if (!args.isSimulatable) {
		return 'required model features are missing for this school-year';
	}
	return null;
}

export function AchievementSimulatorView() {
	const selection = useSimulatorSelection();
	const isDemoMode = selection.selectionMode === 'demo';

	const scenarioState = useSimulatorScenario({
		demoProfile: selection.activeDemoProfile,
		selectionMode: selection.selectionMode,
		selectedSchoolKey: selection.selectedSchoolKey,
		selectedYear: selection.selectedYear,
		isSimulatable: selection.simulationMetadata?.is_simulatable ?? false,
	});

	const controlsDisabled = isDemoMode
		? !scenarioState.scenario
		: !scenarioState.scenario ||
			!scenarioState.baselineQuery.isSuccess ||
			!selection.simulationMetadata?.is_simulatable;

	const runDisabledReason = disabledReason({
		hasScenario: Boolean(scenarioState.scenario),
		isBaselineReady: isDemoMode || scenarioState.baselineQuery.isSuccess,
		hasMetadata: isDemoMode || Boolean(selection.simulationMetadata),
		isSimulatable:
			isDemoMode || Boolean(selection.simulationMetadata?.is_simulatable),
	});

	const chip = statusChip({
		hasSchool: selection.selectedSchoolKey !== null,
		isDemoMode,
		isFetchingBaseline: scenarioState.baselineQuery.isFetching,
		hasMetadata: Boolean(selection.simulationMetadata),
		isSimulatable: Boolean(selection.simulationMetadata?.is_simulatable),
	});

	const metadataError =
		selection.simulationMetadataQuery.error instanceof Error
			? selection.simulationMetadataQuery.error
			: null;
	const baselineError =
		scenarioState.baselineQuery.error instanceof Error
			? scenarioState.baselineQuery.error.message
			: null;

	return (
		<section className="space-y-4">
			<Header
				isDemoMode={isDemoMode}
				statusClassName={chip.className}
				statusLabel={chip.label}
				switchToDemo={() => selection.setSelectionMode('demo')}
				switchToSchool={() => selection.setSelectionMode('school')}
			/>

			<div className="grid gap-4 xl:grid-cols-12">
				<div className="xl:col-span-4">
					{isDemoMode ? (
						<DemoProfilesCard
							activeProfileId={selection.selectedDemoProfileId}
							onOpenMetadata={() =>
								selection.setShowMetadata(true)
							}
							onSelectProfile={selection.setSelectedDemoProfileId}
							profiles={DEMO_PROFILES}
						/>
					) : (
						<SchoolSelectionCard
							metadata={selection.simulationMetadata}
							metadataError={metadataError}
							onOpenMetadata={() =>
								selection.setShowMetadata(true)
							}
							onSchoolChange={(schoolKey) => {
								selection.setSchoolSelection(schoolKey);
								scenarioState.setRunError(null);
							}}
							onYearChange={(year) => {
								selection.setSelectedYear(year);
								scenarioState.setRunError(null);
							}}
							schoolGroups={selection.schoolsByDistrict}
							schoolQuery={selection.schoolQuery}
							selectedSchoolKey={selection.selectedSchoolKey}
							selectedYear={selection.selectedYear}
							setSchoolQuery={selection.setSchoolQuery}
							yearOptions={selection.yearOptions}
						/>
					)}
				</div>

				<div className="xl:col-span-5">
					<ScenarioControlsCard
						activeGroup={scenarioState.activeGroup}
						commitScenario={scenarioState.commitScenario}
						controlsDisabled={controlsDisabled}
						isLocked={scenarioState.isLocked}
						scenario={scenarioState.scenario}
						unlockControls={scenarioState.unlockControls}
						updateNumericField={scenarioState.updateNumericField}
					/>
				</div>

				<div className="xl:col-span-3">
					<OutcomeSnapshotCard
						achievementDelta={scenarioState.achievementDelta}
						achievementPct={scenarioState.achievementPct}
						baselineAchievement={scenarioState.baselineAchievement}
						baselineError={baselineError}
						baselineLoading={scenarioState.baselineQuery.isFetching}
						disabledReason={runDisabledReason}
						isRunning={scenarioState.isRunning}
						raceTotal={scenarioState.raceTotal}
						resetScenario={scenarioState.resetScenario}
						runError={scenarioState.runError}
						scenarioAchievement={scenarioState.scenarioAchievement}
					/>
				</div>
			</div>

			{selection.showMetadata && (
				<SchoolMetadataPopup
					demoProfile={selection.activeDemoProfile}
					metadata={selection.simulationMetadata}
					mode={selection.selectionMode}
					onClose={() => selection.setShowMetadata(false)}
				/>
			)}
		</section>
	);
}

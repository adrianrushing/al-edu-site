import { useMemo } from "react";
import { OutcomeSnapshotCard } from "./components/outcome-snapshot-card";
import { ScenarioControlsCard } from "./components/scenario-controls-card";
import { SchoolMetadataPopup } from "./components/school-metadata-popup";
import { SchoolSelectionCard } from "./components/school-selection-card";
import { useSimulatorScenario } from "./use-simulator-scenario";
import { useSimulatorSelection } from "./use-simulator-selection";

export function AchievementSimulatorView() {
    const {
        schoolQuery,
        schoolsByDistrict,
        selectedSchoolKey,
        selectedYear,
        setSchoolQuery,
        setSchoolSelection,
        setSelectedYear,
        setShowMetadata,
        showMetadata,
        simulationMetadata,
        simulationMetadataQuery,
        yearOptions,
    } = useSimulatorSelection();

    const {
        achievementDelta,
        achievementPct,
        activeGroup,
        baselineAchievement,
        baselineQuery,
        isLocked,
        isRunning,
        raceTotal,
        resetScenario,
        runError,
        runSimulation,
        scenario,
        scenarioAchievement,
        setRunError,
        updateNumericField,
    } = useSimulatorScenario({
        selectedSchoolKey,
        selectedYear,
        isSimulatable: simulationMetadata?.is_simulatable ?? false,
    });

    const controlsDisabled = useMemo(() => {
        return (
            !scenario ||
            !baselineQuery.isSuccess ||
            !simulationMetadata ||
            !simulationMetadata.is_simulatable
        );
    }, [baselineQuery.isSuccess, scenario, simulationMetadata]);

    const canRun =
        Boolean(scenario) &&
        baselineQuery.isSuccess &&
        Boolean(simulationMetadata?.is_simulatable) &&
        !isRunning;

    return (
        <section className="grid gap-4 lg:grid-cols-[340px_1fr]">
            <SchoolSelectionCard
                metadata={simulationMetadata}
                metadataError={
                    simulationMetadataQuery.error instanceof Error
                        ? simulationMetadataQuery.error
                        : null
                }
                onOpenMetadata={() => setShowMetadata(true)}
                onSchoolChange={(schoolKey) => {
                    setSchoolSelection(schoolKey);
                    setRunError(null);
                }}
                onYearChange={(year) => {
                    setSelectedYear(year);
                    setRunError(null);
                }}
                schoolGroups={schoolsByDistrict}
                schoolQuery={schoolQuery}
                selectedSchoolKey={selectedSchoolKey}
                selectedYear={selectedYear}
                setSchoolQuery={setSchoolQuery}
                yearOptions={yearOptions}
            />

            <div className="space-y-4">
                <ScenarioControlsCard
                    activeGroup={activeGroup}
                    controlsDisabled={controlsDisabled}
                    isLocked={isLocked}
                    scenario={scenario}
                    updateNumericField={updateNumericField}
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
                    baselineLoading={baselineQuery.isFetching}
                    canRun={canRun}
                    isRunning={isRunning}
                    raceTotal={raceTotal}
                    resetScenario={resetScenario}
                    runError={runError}
                    runSimulation={runSimulation}
                    scenarioAchievement={scenarioAchievement}
                />
            </div>

            {showMetadata && (
                <SchoolMetadataPopup
                    metadata={simulationMetadata}
                    onClose={() => setShowMetadata(false)}
                />
            )}
        </section>
    );
}

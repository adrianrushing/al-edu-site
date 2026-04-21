import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";

import {
    type BaselineResponse,
    fetchBaseline,
    predictTarget,
    type SimulatorPayload,
} from "@/lib/api";

import { type AdjustableField, demographicKeys, toGroupKey } from "./constants";

type UseSimulatorScenarioParams = {
    selectedSchoolKey: number | null;
    selectedYear: number | undefined;
    isSimulatable: boolean;
};

export function useSimulatorScenario({
    isSimulatable,
    selectedSchoolKey,
    selectedYear,
}: UseSimulatorScenarioParams) {
    const [baseline, setBaseline] = useState<BaselineResponse | null>(null);
    const [scenario, setScenario] = useState<SimulatorPayload | null>(null);
    const [activeGroup, setActiveGroup] = useState<string | null>(null);
    const [isRunning, setIsRunning] = useState(false);
    const [runError, setRunError] = useState<string | null>(null);
    const initializedKeyRef = useRef<string | null>(null);

    const selectionKey = useMemo(() => {
        if (selectedSchoolKey == null || selectedYear == null) {
            return null;
        }
        return `${selectedSchoolKey}:${selectedYear}`;
    }, [selectedSchoolKey, selectedYear]);

    const baselineQuery = useQuery({
        queryKey: ["simulator-baseline", selectedSchoolKey, selectedYear],
        queryFn: () => {
            if (selectedSchoolKey == null || selectedYear == null) {
                throw new Error("Missing school/year selection");
            }
            return fetchBaseline(selectedSchoolKey, selectedYear);
        },
        enabled: selectedSchoolKey !== null && selectedYear !== undefined,
        retry: false,
        staleTime: 60 * 1000,
        refetchOnWindowFocus: false,
    });

    useEffect(() => {
        if (!selectionKey) {
            initializedKeyRef.current = null;
            setBaseline(null);
            setScenario(null);
            setActiveGroup(null);
            setRunError(null);
            return;
        }

        if (initializedKeyRef.current !== selectionKey) {
            setBaseline(null);
            setScenario(null);
            setActiveGroup(null);
            setRunError(null);
        }
    }, [selectionKey]);

    useEffect(() => {
        if (!selectionKey || !baselineQuery.data) {
            return;
        }

        if (initializedKeyRef.current === selectionKey) {
            return;
        }

        initializedKeyRef.current = selectionKey;
        setBaseline(baselineQuery.data);
        setScenario(baselineQuery.data);
        setActiveGroup(null);
        setRunError(null);
    }, [baselineQuery.data, selectionKey]);

    const updateNumericField = (key: AdjustableField, value: number) => {
        const targetGroup = toGroupKey(key);
        if (activeGroup && activeGroup !== targetGroup) {
            return;
        }

        setActiveGroup(targetGroup);
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
            } else if (key === "inexp_rate") {
                next.exp_rate = Math.max(0, Math.min(100, 100 - value));
            }

            return next;
        });
    };

    const resetScenario = () => {
        if (!baseline) {
            return;
        }
        setScenario(baseline);
        setActiveGroup(null);
        setRunError(null);
    };

    const isLocked = (field: AdjustableField) => {
        const targetGroup = toGroupKey(field);
        return Boolean(activeGroup && activeGroup !== targetGroup);
    };

    const runSimulation = async () => {
        if (!scenario || !isSimulatable) {
            return;
        }

        setIsRunning(true);
        setRunError(null);

        try {
            const achResult = await predictTarget("ach_all", scenario);
            setScenario((prev) =>
                prev
                    ? {
                          ...prev,
                          ach_all: achResult.predicted_value,
                      }
                    : prev,
            );
        } catch (error) {
            setRunError(error instanceof Error ? error.message : "Simulation failed");
        } finally {
            setIsRunning(false);
        }
    };

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

    return {
        achievementDelta,
        achievementPct,
        activeGroup,
        baseline,
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
    };
}

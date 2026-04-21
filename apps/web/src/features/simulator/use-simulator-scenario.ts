import { useQuery } from '@tanstack/react-query';
import { useEffect, useMemo, useRef, useState } from 'react';

import {
	type BaselineResponse,
	fetchBaseline,
	predictTarget,
	type SimulatorPayload,
} from '@/lib/api';
import { type AdjustableField, demographicKeys, toGroupKey } from './constants';
import type { DemoProfile } from './demo-profiles';

type UseSimulatorScenarioParams = {
	demoProfile: DemoProfile | undefined;
	selectionMode: 'demo' | 'school';
	selectedSchoolKey: number | null;
	selectedYear: number | undefined;
	isSimulatable: boolean;
};

const PREDICT_SIGNATURE_FIELDS: Array<keyof SimulatorPayload> = [
	'per_pupil_total_raw',
	'nces_poverty',
	'nces_freelunch',
	'exp_rate',
	'inexp_rate',
	'nces_locale_type',
	'is_charter',
	'is_magnet',
	'pct_american_indian_alaska_native',
	'pct_asian',
	'pct_black_or_african_american',
	'pct_native_hawaiian_pacific_islander',
	'pct_two_or_more_races',
	'pct_white',
];

function toPredictSignature(payload: SimulatorPayload) {
	const signaturePayload: Record<string, unknown> = {};
	for (const field of PREDICT_SIGNATURE_FIELDS) {
		signaturePayload[field] = payload[field] ?? null;
	}
	return JSON.stringify(signaturePayload);
}

function getCommitSignature(args: {
	scenario: SimulatorPayload | null;
	selectionMode: 'demo' | 'school';
	isSimulatable: boolean;
	lastCommittedSignature: string | null;
}) {
	if (!args.scenario) {
		return null;
	}

	if (args.selectionMode === 'school' && !args.isSimulatable) {
		return null;
	}

	const signature = toPredictSignature(args.scenario);
	if (signature === args.lastCommittedSignature) {
		return null;
	}

	return signature;
}

function isLatestRequest(
	requestId: number,
	commitRequestIdRef: { current: number },
) {
	return requestId === commitRequestIdRef.current;
}

function runIfLatest(
	requestId: number,
	commitRequestIdRef: { current: number },
	callback: () => void,
) {
	if (!isLatestRequest(requestId, commitRequestIdRef)) {
		return false;
	}
	callback();
	return true;
}

export function useSimulatorScenario({
	demoProfile,
	isSimulatable,
	selectionMode,
	selectedSchoolKey,
	selectedYear,
}: UseSimulatorScenarioParams) {
	const [baseline, setBaseline] = useState<BaselineResponse | null>(null);
	const [scenario, setScenario] = useState<SimulatorPayload | null>(null);
	const [activeGroup, setActiveGroup] = useState<string | null>(null);
	const [isRunning, setIsRunning] = useState(false);
	const [runError, setRunError] = useState<string | null>(null);
	const initializedKeyRef = useRef<string | null>(null);
	const lastCommittedSignatureRef = useRef<string | null>(null);
	const commitRequestIdRef = useRef(0);

	const selectionKey = useMemo(() => {
		if (selectionMode === 'demo') {
			return demoProfile ? `demo:${demoProfile.id}` : null;
		}
		if (selectedSchoolKey == null || selectedYear == null) {
			return null;
		}
		return `${selectedSchoolKey}:${selectedYear}`;
	}, [demoProfile, selectionMode, selectedSchoolKey, selectedYear]);

	const baselineQuery = useQuery({
		queryKey: ['simulator-baseline', selectedSchoolKey, selectedYear],
		queryFn: () => {
			if (selectedSchoolKey == null || selectedYear == null) {
				throw new Error('Missing school/year selection');
			}
			return fetchBaseline(selectedSchoolKey, selectedYear);
		},
		enabled:
			selectionMode === 'school' &&
			selectedSchoolKey !== null &&
			selectedYear !== undefined,
		retry: false,
		staleTime: 60 * 1000,
		refetchOnWindowFocus: false,
	});

	useEffect(() => {
		if (!selectionKey) {
			initializedKeyRef.current = null;
			lastCommittedSignatureRef.current = null;
			setBaseline(null);
			setScenario(null);
			setActiveGroup(null);
			setRunError(null);
			return;
		}

		if (initializedKeyRef.current !== selectionKey) {
			lastCommittedSignatureRef.current = null;
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

		if (selectionMode !== 'school') {
			return;
		}

		if (initializedKeyRef.current === selectionKey) {
			return;
		}

		initializedKeyRef.current = selectionKey;
		lastCommittedSignatureRef.current = null;
		setBaseline(baselineQuery.data);
		setScenario(baselineQuery.data);
		setActiveGroup(null);
		setRunError(null);
	}, [baselineQuery.data, selectionKey, selectionMode]);

	useEffect(() => {
		if (selectionMode !== 'demo' || !selectionKey || !demoProfile) {
			return;
		}

		if (initializedKeyRef.current === selectionKey) {
			return;
		}

		initializedKeyRef.current = selectionKey;
		lastCommittedSignatureRef.current = null;
		setBaseline(demoProfile.baseline);
		setScenario(demoProfile.baseline);
		setActiveGroup(null);
		setRunError(null);
	}, [demoProfile, selectionKey, selectionMode]);

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

			if (key === 'exp_rate') {
				next.inexp_rate = Math.max(0, Math.min(100, 100 - value));
			} else if (key === 'inexp_rate') {
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

	const unlockControls = () => {
		setActiveGroup(null);
	};

	const isLocked = (field: AdjustableField) => {
		const targetGroup = toGroupKey(field);
		return Boolean(activeGroup && activeGroup !== targetGroup);
	};

	const commitScenario = async () => {
		const signature = getCommitSignature({
			scenario,
			selectionMode,
			isSimulatable,
			lastCommittedSignature: lastCommittedSignatureRef.current,
		});
		if (signature == null) {
			return;
		}

		const requestId = commitRequestIdRef.current + 1;
		commitRequestIdRef.current = requestId;

		setIsRunning(true);
		setRunError(null);

		try {
			const achResult = await predictTarget(
				'ach_all',
				scenario as SimulatorPayload,
			);
			runIfLatest(requestId, commitRequestIdRef, () => {
				setScenario((prev) =>
					prev
						? {
								...prev,
								ach_all: achResult.predicted_value,
							}
						: prev,
				);
				lastCommittedSignatureRef.current = signature;
			});
		} catch (error) {
			runIfLatest(requestId, commitRequestIdRef, () => {
				setRunError(
					error instanceof Error
						? error.message
						: 'Simulation failed',
				);
			});
		} finally {
			runIfLatest(requestId, commitRequestIdRef, () => {
				setIsRunning(false);
			});
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
			? ((scenarioAchievement - baselineAchievement) /
					baselineAchievement) *
				100
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
		unlockControls,
		runError,
		commitScenario,
		scenario,
		scenarioAchievement,
		setRunError,
		updateNumericField,
	};
}

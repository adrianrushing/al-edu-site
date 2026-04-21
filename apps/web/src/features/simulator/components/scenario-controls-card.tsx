import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import type { SimulatorPayload } from "@/lib/api";

import {
    type AdjustableField,
    demographicKeys,
    formatDemographicLabel,
} from "../constants";
import { RangeField } from "./shared";

type ScenarioControlsCardProps = {
    activeGroup: string | null;
    controlsDisabled: boolean;
    isLocked: (field: AdjustableField) => boolean;
    scenario: SimulatorPayload | null;
    updateNumericField: (key: AdjustableField, value: number) => void;
};

type SliderConfig = {
    key: AdjustableField;
    label: string;
    max: number;
    min: number;
    step: number;
    suffix?: string;
    getValue: (scenario: SimulatorPayload | null) => number;
    setValue: (value: number) => number;
};

const coreSliderConfigs: SliderConfig[] = [
    {
        key: "per_pupil_total_raw",
        label: "Per pupil funding",
        max: 30000,
        min: 4000,
        step: 100,
        suffix: "$",
        getValue: (scenario) => Number(scenario?.per_pupil_total_raw ?? 0),
        setValue: (value) => value,
    },
    {
        key: "nces_poverty",
        label: "Poverty rate",
        max: 100,
        min: 0,
        step: 1,
        suffix: "%",
        getValue: (scenario) => Number(scenario?.nces_poverty ?? 0) * 100,
        setValue: (value) => value / 100,
    },
    {
        key: "nces_freelunch",
        label: "Free lunch count",
        max: 2500,
        min: 0,
        step: 1,
        getValue: (scenario) => Number(scenario?.nces_freelunch ?? 0),
        setValue: (value) => value,
    },
    {
        key: "exp_rate",
        label: "Experienced teacher rate",
        max: 100,
        min: 0,
        step: 0.5,
        suffix: "%",
        getValue: (scenario) => Number(scenario?.exp_rate ?? 0),
        setValue: (value) => value,
    },
    {
        key: "inexp_rate",
        label: "Inexperienced teacher rate",
        max: 100,
        min: 0,
        step: 0.5,
        suffix: "%",
        getValue: (scenario) => Number(scenario?.inexp_rate ?? 0),
        setValue: (value) => value,
    },
];

export function ScenarioControlsCard({
    activeGroup,
    controlsDisabled,
    isLocked,
    scenario,
    updateNumericField,
}: ScenarioControlsCardProps) {
    const isDisabled = (field: AdjustableField) => {
        return controlsDisabled || isLocked(field);
    };

    return (
        <Card>
            <CardHeader>
                <CardTitle>Scenario Controls</CardTitle>
                <CardDescription>
                    Change one variable group at a time. Teacher experience rates are
                    linked complements.
                </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
                {coreSliderConfigs.map((config) => (
                    <RangeField
                        disabled={isDisabled(config.key)}
                        key={config.key}
                        label={config.label}
                        max={config.max}
                        min={config.min}
                        onChange={(value) =>
                            updateNumericField(config.key, config.setValue(value))
                        }
                        step={config.step}
                        suffix={config.suffix}
                        value={config.getValue(scenario)}
                    />
                ))}

                {demographicKeys.map((key) => (
                    <RangeField
                        disabled={isDisabled(key)}
                        key={key}
                        label={formatDemographicLabel(key)}
                        max={100}
                        min={0}
                        onChange={(value) => updateNumericField(key, value / 100)}
                        step={1}
                        suffix="%"
                        value={Number(scenario?.[key] ?? 0) * 100}
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

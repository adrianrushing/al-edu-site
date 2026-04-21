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
import type { SchoolSimulationMetadataResponse } from "@/lib/api";

import type { SchoolDistrictGroup } from "../use-simulator-selection";
import { Field } from "./shared";

type SchoolSelectionCardProps = {
    metadata: SchoolSimulationMetadataResponse | undefined;
    metadataError: Error | null;
    onOpenMetadata: () => void;
    onSchoolChange: (schoolKey: number | null) => void;
    onYearChange: (year: number | undefined) => void;
    schoolGroups: SchoolDistrictGroup[];
    schoolQuery: string;
    selectedSchoolKey: number | null;
    selectedYear: number | undefined;
    setSchoolQuery: (value: string) => void;
    yearOptions: number[];
};

export function SchoolSelectionCard({
    metadata,
    metadataError,
    onOpenMetadata,
    onSchoolChange,
    onYearChange,
    schoolGroups,
    schoolQuery,
    selectedSchoolKey,
    selectedYear,
    setSchoolQuery,
    yearOptions,
}: SchoolSelectionCardProps) {
    return (
        <Card>
            <CardHeader>
                <CardTitle>School Baseline</CardTitle>
                <CardDescription>
                    Select a school and load baseline model inputs.
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
                <Field label="Year">
                    <Select
                        onChange={(event) => {
                            onYearChange(
                                event.target.value
                                    ? Number(event.target.value)
                                    : undefined,
                            );
                        }}
                        value={selectedYear?.toString() ?? ""}
                    >
                        <option value="">Select year</option>
                        {yearOptions.map((year) => (
                            <option key={year} value={year}>
                                {year}
                            </option>
                        ))}
                    </Select>
                </Field>

                <Field label="School search">
                    <Input
                        onChange={(event) => setSchoolQuery(event.target.value)}
                        placeholder="Type district or school"
                        value={schoolQuery}
                    />
                </Field>

                <Field label="School">
                    <Select
                        onChange={(event) => {
                            onSchoolChange(
                                event.target.value ? Number(event.target.value) : null,
                            );
                        }}
                        value={selectedSchoolKey?.toString() ?? ""}
                    >
                        <option value="">Select school</option>
                        {schoolGroups.map((group) => (
                            <optgroup key={group.districtName} label={group.districtName}>
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

                {metadata && !metadata.is_simulatable && (
                    <p className="text-xs text-amber-700">
                        Selected year is not simulatable. Missing fields:{" "}
                        {metadata.missing_features.join(", ") || "Unknown"}
                    </p>
                )}

                {metadataError && (
                    <p className="text-xs text-red-600">{metadataError.message}</p>
                )}

                <Button disabled={!metadata} onClick={onOpenMetadata} variant="outline">
                    View Data Metadata
                </Button>
            </CardContent>
        </Card>
    );
}

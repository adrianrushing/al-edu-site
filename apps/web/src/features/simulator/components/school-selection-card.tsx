import { Button } from '@/components/ui/button';
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import type { SchoolSimulationMetadataResponse } from '@/lib/api';

import type { SchoolDistrictGroup } from '../use-simulator-selection';
import { Field } from './shared';

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

function StatusPill({ isSimulatable }: { isSimulatable: boolean | undefined }) {
	if (isSimulatable === undefined) {
		return (
			<span className="rounded-full border px-2 py-0.5 text-xs text-muted-foreground">
				Select school
			</span>
		);
	}

	return isSimulatable ? (
		<span className="rounded-full border border-emerald-300 bg-emerald-50 px-2 py-0.5 text-xs text-emerald-700">
			Ready
		</span>
	) : (
		<span className="rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-xs text-amber-700">
			Data incomplete
		</span>
	);
}

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
				<div className="flex items-center justify-between gap-2">
					<CardTitle>1. School and Year</CardTitle>
					<StatusPill isSimulatable={metadata?.is_simulatable} />
				</div>
				<CardDescription>
					Choose a school baseline and year before adjusting scenario
					levers.
				</CardDescription>
			</CardHeader>
			<CardContent className="space-y-4">
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
								event.target.value
									? Number(event.target.value)
									: null,
							);
						}}
						value={selectedSchoolKey?.toString() ?? ''}
					>
						<option value="">Select school</option>
						{schoolGroups.map((group) => (
							<optgroup
								key={group.districtName}
								label={group.districtName}
							>
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

				<Field label="Year">
					<Select
						disabled={selectedSchoolKey == null}
						onChange={(event) => {
							onYearChange(
								event.target.value
									? Number(event.target.value)
									: undefined,
							);
						}}
						value={selectedYear?.toString() ?? ''}
					>
						<option value="">Select year</option>
						{yearOptions.map((year) => (
							<option key={year} value={year}>
								{year}
							</option>
						))}
					</Select>
				</Field>

				<div className="rounded-md border bg-muted/30 p-3 text-xs text-muted-foreground">
					<p>Latest year: {metadata?.latest_year ?? '--'}</p>
					<p>
						Latest simulatable:{' '}
						{metadata?.latest_simulatable_year ?? '--'}
					</p>
					<p>
						Selected status:{' '}
						{metadata
							? metadata.is_simulatable
								? 'Ready'
								: 'Missing fields'
							: '--'}
					</p>
				</div>

				{metadata && !metadata.is_simulatable && (
					<p className="text-xs text-amber-700">
						This year is not simulatable. Open Data Details to
						review missing features.
					</p>
				)}

				{metadataError && (
					<p className="text-xs text-red-600">
						{metadataError.message}
					</p>
				)}

				<Button
					disabled={!metadata}
					onClick={onOpenMetadata}
					variant="outline"
				>
					View Data Details
				</Button>
			</CardContent>
		</Card>
	);
}

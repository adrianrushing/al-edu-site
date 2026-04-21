import { Button } from '@/components/ui/button';
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from '@/components/ui/card';
import type { SchoolSimulationMetadataResponse } from '@/lib/api';

import { DEMO_MODEL_FEATURES, type DemoProfile } from '../demo-profiles';

function DemoDetails({
	demoProfile,
}: {
	demoProfile: DemoProfile | undefined;
}) {
	return (
		<>
			<div className="rounded-md border p-3">
				<p>Source: Demonstrative profile</p>
				<p>Profile: {demoProfile?.label ?? '-'}</p>
				<p>Assumption set: static placeholder baseline values</p>
			</div>
			<div className="space-y-2">
				<p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
					Profile assumptions
				</p>
				<p className="rounded-md border p-2 text-xs">
					{demoProfile?.description ?? 'No profile selected.'}
				</p>
			</div>
			<div className="space-y-2">
				<p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
					Model features (ach_all)
				</p>
				<p className="rounded-md border p-2 text-xs">
					{DEMO_MODEL_FEATURES.join(', ')}
				</p>
			</div>
		</>
	);
}

function SchoolDetails({
	metadata,
}: {
	metadata: SchoolSimulationMetadataResponse | undefined;
}) {
	return (
		<>
			<div className="rounded-md border p-3">
				<p>Latest year: {metadata?.latest_year ?? '-'}</p>
				<p>
					Latest simulatable year:{' '}
					{metadata?.latest_simulatable_year ?? '-'}
				</p>
				<p>Selected year: {metadata?.selected_year ?? '-'}</p>
				<p>Simulatable: {metadata?.is_simulatable ? 'Yes' : 'No'}</p>
			</div>
			<div className="space-y-2">
				<p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
					Year readiness
				</p>
				<div className="overflow-hidden rounded-md border text-xs">
					<table className="w-full">
						<thead className="bg-muted/40">
							<tr>
								<th className="px-2 py-1 text-left">Year</th>
								<th className="px-2 py-1 text-left">Status</th>
								<th className="px-2 py-1 text-left">Missing</th>
							</tr>
						</thead>
						<tbody>
							{metadata?.year_status.map((status) => (
								<tr className="border-t" key={status.year}>
									<td className="px-2 py-1">{status.year}</td>
									<td className="px-2 py-1">
										{status.is_simulatable
											? 'Ready'
											: 'Missing data'}
									</td>
									<td className="px-2 py-1">
										{status.missing_features.length}
									</td>
								</tr>
							))}
						</tbody>
					</table>
				</div>
			</div>
			<div className="space-y-2">
				<p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
					Missing required features (selected year)
				</p>
				<p className="rounded-md border p-2 text-xs">
					{metadata?.missing_features.length
						? metadata.missing_features.join(', ')
						: 'None'}
				</p>
			</div>
			<div className="space-y-2">
				<p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
					Model features (ach_all)
				</p>
				<p className="rounded-md border p-2 text-xs">
					{metadata?.required_features.length
						? metadata.required_features.join(', ')
						: 'Unavailable'}
				</p>
			</div>
		</>
	);
}

export function SchoolMetadataPopup({
	demoProfile,
	metadata,
	mode,
	onClose,
}: {
	demoProfile: DemoProfile | undefined;
	metadata: SchoolSimulationMetadataResponse | undefined;
	mode: 'demo' | 'school';
	onClose: () => void;
}) {
	return (
		<div className="fixed inset-0 z-50 bg-black/30">
			<aside className="absolute inset-y-0 right-0 w-[520px] border-l bg-background p-4 shadow-xl">
				<Card className="h-full">
					<CardHeader>
						<CardTitle>Data Details</CardTitle>
						<CardDescription>
							Year readiness and model feature coverage.
						</CardDescription>
					</CardHeader>
					<CardContent className="space-y-4 overflow-y-auto text-sm">
						{mode === 'demo' ? (
							<DemoDetails demoProfile={demoProfile} />
						) : (
							<SchoolDetails metadata={metadata} />
						)}
						<Button onClick={onClose} variant="outline">
							Close
						</Button>
					</CardContent>
				</Card>
			</aside>
		</div>
	);
}

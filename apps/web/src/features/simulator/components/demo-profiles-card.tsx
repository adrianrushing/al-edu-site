import { Button } from '@/components/ui/button';
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from '@/components/ui/card';

import type { DemoProfile } from '../demo-profiles';

type DemoProfilesCardProps = {
	activeProfileId: DemoProfile['id'];
	onOpenMetadata: () => void;
	onSelectProfile: (id: DemoProfile['id']) => void;
	profiles: DemoProfile[];
};

export function DemoProfilesCard({
	activeProfileId,
	onOpenMetadata,
	onSelectProfile,
	profiles,
}: DemoProfilesCardProps) {
	return (
		<Card>
			<CardHeader>
				<CardTitle>1. Demonstrative School Profiles</CardTitle>
				<CardDescription>
					Start with representative high, median, or low achievement
					baselines.
				</CardDescription>
			</CardHeader>
			<CardContent className="space-y-2">
				{profiles.map((profile) => {
					const isActive = profile.id === activeProfileId;
					return (
						<button
							className={`w-full rounded-md border p-3 text-left transition ${isActive ? 'border-emerald-300 bg-emerald-50' : 'bg-background hover:bg-muted/30'}`}
							key={profile.id}
							onClick={() => onSelectProfile(profile.id)}
							type="button"
						>
							<p className="text-sm font-medium">
								{profile.label}
							</p>
							<p className="text-xs text-muted-foreground">
								{profile.description}
							</p>
						</button>
					);
				})}

				<div className="pt-1">
					<Button onClick={onOpenMetadata} variant="outline">
						View Data Details
					</Button>
				</div>
			</CardContent>
		</Card>
	);
}

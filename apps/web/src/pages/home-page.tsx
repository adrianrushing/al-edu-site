import { useQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';

import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from '@/components/ui/card';
import { fetchDatasets } from '@/lib/api';

const MILLISECONDS_PER_SECOND = 1000;
const SECONDS_PER_MINUTE = 60;
const METADATA_GC_MINUTES = 30;
const METADATA_STALE_TIME_MS =
	10 * SECONDS_PER_MINUTE * MILLISECONDS_PER_SECOND;
const METADATA_GC_TIME_MS =
	METADATA_GC_MINUTES * SECONDS_PER_MINUTE * MILLISECONDS_PER_SECOND;

export function HomePage() {
	const datasetsQuery = useQuery({
		queryKey: ['datasets'],
		queryFn: fetchDatasets,
		staleTime: METADATA_STALE_TIME_MS,
		gcTime: METADATA_GC_TIME_MS,
	});

	return (
		<section className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
			{datasetsQuery.data?.map((dataset) => (
				<Card key={dataset.key}>
					<CardHeader>
						<CardTitle>
							{dataset.key.replaceAll('_', ' ')}
						</CardTitle>
						<CardDescription>{dataset.description}</CardDescription>
					</CardHeader>
					<CardContent>
						<Link
							className="text-sm font-semibold text-primary hover:underline"
							search={{
								dataset: dataset.key,
								limit: 50,
								offset: 0,
							}}
							to="/download"
						>
							Open dataset
						</Link>
					</CardContent>
				</Card>
			))}
			{!datasetsQuery.data && (
				<Card>
					<CardContent className="pt-6 text-sm text-muted-foreground">
						Loading datasets...
					</CardContent>
				</Card>
			)}
		</section>
	);
}

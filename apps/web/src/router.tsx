import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
	createRootRoute,
	createRoute,
	createRouter,
	Link,
	Outlet,
	RouterProvider,
	useNavigate,
} from '@tanstack/react-router';
import { z } from 'zod';

import { AchievementSimulatorPage } from '@/pages/achievement-simulator-page';
import { DistrictsPage } from '@/pages/districts-page';
import { DownloadPage } from '@/pages/download-page';
import { HomePage } from '@/pages/home-page';
import { RankingsPage } from '@/pages/rankings-page';
import type {
	DistrictSearch,
	DownloadSearch,
	RankingsSearch,
} from '@/pages/types';

const queryClient = new QueryClient();
const DEFAULT_DOWNLOAD_LIMIT = 50;
const DEFAULT_RANKINGS_LIMIT = 25;

const rootRoute = createRootRoute({
	component: () => (
		<div className="w-full px-4 py-6 sm:px-6 lg:px-8">
			<header className="mb-6 flex flex-col gap-3 rounded-lg border bg-card/80 p-5 backdrop-blur-sm md:flex-row md:items-center md:justify-between">
				<div>
					<h1 className="text-2xl font-black tracking-tight">
						EFLT Data Download Console
					</h1>
					<p className="text-sm text-muted-foreground">
						Filter state education data and export clean CSVs in
						seconds.
					</p>
				</div>
				<nav className="flex gap-2">
					<Link
						className="rounded-md px-3 py-2 text-sm font-medium hover:bg-muted data-[status=active]:bg-muted"
						to="/"
					>
						Home
					</Link>
					<Link
						className="rounded-md px-3 py-2 text-sm font-medium hover:bg-muted data-[status=active]:bg-muted"
						search={{ limit: DEFAULT_DOWNLOAD_LIMIT, offset: 0 }}
						to="/download"
					>
						Download
					</Link>
					<Link
						className="rounded-md px-3 py-2 text-sm font-medium hover:bg-muted data-[status=active]:bg-muted"
						search={{}}
						to="/districts"
					>
						Districts
					</Link>
					<Link
						className="rounded-md px-3 py-2 text-sm font-medium hover:bg-muted data-[status=active]:bg-muted"
						search={{}}
						to="/simulator"
					>
						Simulator
					</Link>
					<Link
						className="rounded-md px-3 py-2 text-sm font-medium hover:bg-muted data-[status=active]:bg-muted"
						search={{ limit: DEFAULT_RANKINGS_LIMIT }}
						to="/rankings"
					>
						Rankings
					</Link>
				</nav>
			</header>
			<Outlet />
		</div>
	),
});

const homeRoute = createRoute({
	getParentRoute: () => rootRoute,
	path: '/',
	component: HomePage,
});

const downloadSearch = z.object({
	dataset: z.string().optional(),
	year: z.coerce.number().optional(),
	district: z.string().optional(),
	school: z.string().optional(),
	school_key: z.coerce.number().optional(),
	gender: z.string().optional(),
	race: z.string().optional(),
	ethnicity: z.string().optional(),
	sub_population: z.string().optional(),
	grade: z.string().optional(),
	limit: z.coerce.number().optional().default(DEFAULT_DOWNLOAD_LIMIT),
	offset: z.coerce.number().optional().default(0),
});

const downloadRoute = createRoute({
	getParentRoute: () => rootRoute,
	path: '/download',
	validateSearch: (search) => downloadSearch.parse(search),
	component: DownloadRoutePage,
});

const districtSearch = z.object({
	year: z.coerce.number().optional(),
	district: z.string().optional(),
	school: z.string().optional(),
});

const districtsRoute = createRoute({
	getParentRoute: () => rootRoute,
	path: '/districts',
	validateSearch: (search) => districtSearch.parse(search),
	component: DistrictsRoutePage,
});

const simulatorRoute = createRoute({
	getParentRoute: () => rootRoute,
	path: '/simulator',
	component: AchievementSimulatorPage,
});

const rankingsSearch = z.object({
	year: z.coerce.number().optional(),
	limit: z.coerce.number().optional().default(DEFAULT_RANKINGS_LIMIT),
	cursor: z.string().optional(),
});

const rankingsRoute = createRoute({
	getParentRoute: () => rootRoute,
	path: '/rankings',
	validateSearch: (search) => rankingsSearch.parse(search),
	component: RankingsRoutePage,
});

const routeTree = rootRoute.addChildren([
	homeRoute,
	downloadRoute,
	districtsRoute,
	simulatorRoute,
	rankingsRoute,
]);

const router = createRouter({ routeTree });

declare module '@tanstack/react-router' {
	interface Register {
		router: typeof router;
	}
}

export function AppRouter() {
	return (
		<QueryClientProvider client={queryClient}>
			<RouterProvider router={router} />
		</QueryClientProvider>
	);
}

function DownloadRoutePage() {
	const search = downloadRoute.useSearch();
	const navigate = useNavigate({ from: '/download' });

	return (
		<DownloadPage
			search={search as DownloadSearch}
			setSearch={(updater, options) =>
				navigate({
					replace: options?.replace,
					search: (prev) => updater(prev as DownloadSearch),
				})
			}
		/>
	);
}

function DistrictsRoutePage() {
	const search = districtsRoute.useSearch();
	const navigate = useNavigate({ from: '/districts' });

	return (
		<DistrictsPage
			search={search as DistrictSearch}
			setSearch={(updater, options) =>
				navigate({
					replace: options?.replace,
					search: (prev) => updater(prev as DistrictSearch),
				})
			}
		/>
	);
}

function RankingsRoutePage() {
	const search = rankingsRoute.useSearch();
	const navigate = useNavigate({ from: '/rankings' });

	return (
		<RankingsPage
			search={search as RankingsSearch}
			setSearch={(updater, options) =>
				navigate({
					replace: options?.replace,
					search: (prev) => updater(prev as RankingsSearch),
				})
			}
		/>
	);
}

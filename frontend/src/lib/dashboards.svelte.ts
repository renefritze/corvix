/**
 * Dashboard selection + URL normalization, ported from `useDashboardState.ts`.
 *
 * The active name comes from the `/dashboards/:name` route match. Unknown names
 * fall back to the first configured dashboard. `fetchKey` is a `$derived` so the
 * default-dashboard snapshot is fetched once with an undefined key and resolving
 * `/` → `/dashboards/<default>` does not change the key (no refetch on
 * normalization). Only user-initiated selections push history; normalization
 * replaces.
 */
import type { Router } from "./router.svelte";
import type { SnapshotStore } from "./snapshot.svelte";

const DASHBOARD_PATH_PREFIX = "/dashboards/";

export class DashboardsStore {
	readonly #router: Router;
	readonly #snapshot: SnapshotStore;
	#userNavigated = false;
	#defaultName = $state<string | undefined>(undefined);

	constructor(router: Router, snapshot: SnapshotStore) {
		this.#router = router;
		this.#snapshot = snapshot;
	}

	fetchKey = $derived.by<string | undefined>(() => {
		const dashboard = this.#router.route.name;
		return dashboard && dashboard !== this.#defaultName ? dashboard : undefined;
	});

	get dashboardNames(): string[] {
		return this.#snapshot.snapshot?.dashboard_names ?? [];
	}

	get currentDashboard(): string | null {
		const dashboard = this.#router.route.name;
		const known =
			dashboard && this.dashboardNames.includes(dashboard)
				? dashboard
				: undefined;
		return known ?? this.dashboardNames[0] ?? null;
	}

	#dashboardPath(name: string | undefined): string {
		const search = this.#router.search;
		if (!name) {
			return `/${search}`;
		}
		return `${DASHBOARD_PATH_PREFIX}${encodeURIComponent(name)}${search}`;
	}

	setDashboard = (name: string | undefined): void => {
		this.#userNavigated = true;
		this.#router.navigate(this.#dashboardPath(name));
	};

	bind(): void {
		// Record the authoritative default name from the default-dashboard
		// snapshot (fetchKey undefined) without touching the fetch key.
		$effect(() => {
			if (this.fetchKey === undefined && this.dashboardNames.length > 0) {
				this.#defaultName = this.dashboardNames[0];
			}
		});

		// Drive the snapshot subscription off the memoized fetch key.
		this.#snapshot.bind(() => this.fetchKey);

		// Normalize the URL to the resolved dashboard once the name list is known.
		$effect(() => {
			if (globalThis.window === undefined) return;
			const dashboard = this.#router.route.name;
			const names = this.dashboardNames;
			if (dashboard !== undefined && names.length === 0) return;
			if (names.length === 0) return;
			const targetPath = this.#dashboardPath(this.currentDashboard ?? undefined);
			const currentPath = `${globalThis.window.location.pathname}${globalThis.window.location.search}`;
			if (currentPath === targetPath) {
				this.#userNavigated = false;
				return;
			}
			if (!this.#userNavigated) {
				this.#router.navigate(targetPath, true);
			}
			this.#userNavigated = false;
		});
	}
}

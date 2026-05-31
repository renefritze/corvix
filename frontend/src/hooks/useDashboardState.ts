import { getCurrentUrl, route } from "preact-router";
import { useCallback, useEffect, useRef } from "preact/hooks";
import { useSnapshot } from "./useSnapshot";

const DASHBOARD_PATH_PREFIX = "/dashboards/";

/** Returns the query string (including leading "?") of the current URL. */
function currentSearch(): string {
	const url = getCurrentUrl();
	const index = url.indexOf("?");
	return index === -1 ? "" : url.slice(index);
}

function dashboardPath(name: string | undefined): string {
	if (!name) {
		return `/${currentSearch()}`;
	}
	return `${DASHBOARD_PATH_PREFIX}${encodeURIComponent(name)}${currentSearch()}`;
}

/**
 * Owns dashboard selection and keeps it in sync with the URL, fetching the
 * matching snapshot. The active name comes from the `/dashboards/:name` route
 * match (preact-router decodes it for us). Falls back to the first configured
 * dashboard when the selected name is unknown (e.g. after navigating to a
 * stale link).
 *
 * Only user-initiated selections push a new history entry; automatic
 * normalization (initial load, falling back from an unknown name) replaces the
 * current entry so the back button can't get stuck in a redirect loop.
 * Back/forward navigation is handled by preact-router, which re-renders the
 * matched route with the new `name`.
 */
export function useDashboardState(routeName?: string) {
	// True when the pending dashboard change came from a user action (the
	// picker) rather than from URL normalization, so the next sync pushes.
	const userNavigated = useRef(false);

	const dashboard = routeName;
	// The default dashboard is fetched with an undefined key (the API returns
	// it). Track the resolved default name so that resolving the implicit `/` to
	// `/dashboards/<first>` does not change the fetch key (and trigger a second
	// fetch); an explicit name equal to the known default maps back to undefined.
	// This preserves the original single-fetch-on-load behaviour.
	const defaultNameRef = useRef<string | undefined>(undefined);
	const fetchKey =
		dashboard && dashboard !== defaultNameRef.current ? dashboard : undefined;
	const snapshotState = useSnapshot(fetchKey);
	const dashboardNames = snapshotState.snapshot?.dashboard_names ?? [];
	// Only the default-dashboard snapshot (fetchKey undefined) tells us the
	// authoritative first name; a non-default fetch returns the same name list
	// but we must not overwrite the default with the active dashboard. Recorded
	// in an effect rather than during render to keep rendering side-effect free.
	useEffect(() => {
		if (fetchKey === undefined && dashboardNames.length > 0) {
			defaultNameRef.current = dashboardNames[0];
		}
	}, [fetchKey, dashboardNames]);

	// An unknown name (stale link) resolves to the default dashboard.
	const knownDashboard =
		dashboard && dashboardNames.includes(dashboard) ? dashboard : undefined;
	const currentDashboard = knownDashboard ?? dashboardNames[0] ?? null;

	const setDashboard = useCallback((name: string | undefined) => {
		userNavigated.current = true;
		route(dashboardPath(name));
	}, []);

	useEffect(() => {
		if (globalThis.window === undefined) {
			return;
		}
		// Wait for the snapshot's dashboard list before normalizing; otherwise we
		// would redirect a valid (but not-yet-loaded) name to the default. Reading
		// `dashboard` (the route name) here also makes it a real dependency so the
		// effect re-runs to fix the URL when navigating to a stale/unknown name
		// that resolves back to the unchanged default.
		if (dashboard !== undefined && dashboardNames.length === 0) {
			return;
		}
		if (dashboardNames.length === 0) {
			return;
		}
		const targetPath = dashboardPath(currentDashboard ?? undefined);
		const currentPath = `${globalThis.window.location.pathname}${globalThis.window.location.search}`;
		if (currentPath === targetPath) {
			userNavigated.current = false;
			return;
		}
		// Normalization (root path, unknown name) replaces; user-initiated
		// navigation already pushed via setDashboard.
		if (!userNavigated.current) {
			route(targetPath, true);
		}
		userNavigated.current = false;
	}, [currentDashboard, dashboard, dashboardNames]);

	return {
		...snapshotState,
		dashboard,
		setDashboard,
		dashboardNames,
		currentDashboard,
	};
}

import { useCallback, useEffect, useRef, useState } from "preact/hooks";
import { useSnapshot } from "./useSnapshot";

const DASHBOARD_PATH_PREFIX = "/dashboards/";

export function parseDashboardFromPath(pathname: string): string | undefined {
	if (!pathname.startsWith(DASHBOARD_PATH_PREFIX)) {
		return undefined;
	}
	const rawName = pathname.slice(DASHBOARD_PATH_PREFIX.length);
	if (!rawName) {
		return undefined;
	}
	return decodeURIComponent(rawName);
}

function dashboardPath(name: string | undefined): string {
	if (!name) {
		return "/";
	}
	return `${DASHBOARD_PATH_PREFIX}${encodeURIComponent(name)}`;
}

/**
 * Owns dashboard selection and keeps it in sync with the URL, fetching the
 * matching snapshot. Falls back to the first configured dashboard when the
 * selected name is unknown (e.g. after navigating to a stale link).
 *
 * Only user-initiated selections push a new history entry; automatic
 * normalization (initial load, popstate, falling back from an unknown name)
 * replaces the current entry so the back button can't get stuck in a redirect
 * loop.
 */
export function useDashboardState() {
	const [dashboard, setDashboardState] = useState<string | undefined>(() => {
		if (globalThis.window === undefined) {
			return undefined;
		}
		return parseDashboardFromPath(globalThis.window.location.pathname);
	});
	// True when the pending dashboard change came from a user action (the
	// picker) rather than from URL normalization, so the next sync pushes.
	const userNavigated = useRef(false);

	const snapshotState = useSnapshot(dashboard);
	const dashboardNames = snapshotState.snapshot?.dashboard_names ?? [];
	const currentDashboard = dashboard ?? dashboardNames[0] ?? null;

	// Expose the latest names to the popstate listener without re-subscribing
	// it on every snapshot refresh (which happens every 15s).
	const dashboardNamesRef = useRef(dashboardNames);
	dashboardNamesRef.current = dashboardNames;

	const setDashboard = useCallback((name: string | undefined) => {
		userNavigated.current = true;
		setDashboardState(name);
	}, []);

	useEffect(() => {
		if (globalThis.window === undefined) {
			return;
		}
		const handlePopState = () => {
			const fromPath = parseDashboardFromPath(
				globalThis.window.location.pathname,
			);
			const names = dashboardNamesRef.current;
			if (fromPath && names.length > 0 && !names.includes(fromPath)) {
				setDashboardState(undefined);
				return;
			}
			setDashboardState(fromPath);
		};
		globalThis.window.addEventListener("popstate", handlePopState);
		return () =>
			globalThis.window.removeEventListener("popstate", handlePopState);
	}, []);

	useEffect(() => {
		if (globalThis.window === undefined) {
			return;
		}
		if (dashboardNames.length === 0) {
			return;
		}
		if (dashboard && !dashboardNames.includes(dashboard)) {
			setDashboardState(undefined);
		}
	}, [dashboard, dashboardNames]);

	useEffect(() => {
		if (globalThis.window === undefined) {
			return;
		}
		const targetPath = dashboardPath(currentDashboard ?? undefined);
		if (globalThis.window.location.pathname === targetPath) {
			userNavigated.current = false;
			return;
		}
		if (userNavigated.current) {
			globalThis.window.history.pushState({}, "", targetPath);
			userNavigated.current = false;
		} else {
			globalThis.window.history.replaceState({}, "", targetPath);
		}
		// `dashboard` is included so that resetting an unknown name to the
		// default (which leaves `currentDashboard` unchanged) still re-syncs the
		// URL, e.g. after navigating back to a stale dashboard link.
	}, [currentDashboard, dashboard]);

	return {
		...snapshotState,
		dashboard,
		setDashboard,
		dashboardNames,
		currentDashboard,
	};
}

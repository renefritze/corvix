import { useEffect, useState } from "preact/hooks";
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
 */
export function useDashboardState() {
	const [dashboard, setDashboard] = useState<string | undefined>(() => {
		if (typeof globalThis.window === "undefined") {
			return undefined;
		}
		return parseDashboardFromPath(globalThis.window.location.pathname);
	});

	const snapshotState = useSnapshot(dashboard);
	const dashboardNames = snapshotState.snapshot?.dashboard_names ?? [];
	const currentDashboard = dashboard ?? dashboardNames[0] ?? null;

	useEffect(() => {
		if (typeof globalThis.window === "undefined") {
			return;
		}
		const handlePopState = () => {
			const fromPath = parseDashboardFromPath(
				globalThis.window.location.pathname,
			);
			if (!fromPath) {
				setDashboard(undefined);
				return;
			}
			if (dashboardNames.length > 0 && !dashboardNames.includes(fromPath)) {
				setDashboard(undefined);
				return;
			}
			setDashboard(fromPath);
		};
		globalThis.window.addEventListener("popstate", handlePopState);
		return () =>
			globalThis.window.removeEventListener("popstate", handlePopState);
	}, [dashboardNames]);

	useEffect(() => {
		if (typeof globalThis.window === "undefined") {
			return;
		}
		if (dashboardNames.length === 0) {
			return;
		}
		if (dashboard && !dashboardNames.includes(dashboard)) {
			setDashboard(undefined);
		}
	}, [dashboard, dashboardNames]);

	useEffect(() => {
		if (typeof globalThis.window === "undefined") {
			return;
		}
		const targetPath = dashboardPath(currentDashboard ?? undefined);
		if (globalThis.window.location.pathname === targetPath) {
			return;
		}
		globalThis.window.history.pushState({}, "", targetPath);
	}, [currentDashboard]);

	return {
		...snapshotState,
		dashboard,
		setDashboard,
		dashboardNames,
		currentDashboard,
	};
}

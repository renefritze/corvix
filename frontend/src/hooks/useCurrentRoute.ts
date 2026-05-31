import { exec, getCurrentUrl } from "preact-router";

const DASHBOARD_ROUTE = "/dashboards/:name";

export interface CurrentRoute {
	/** The decoded dashboard name when on `/dashboards/:name`, else undefined. */
	readonly name: string | undefined;
	/** True for `/`, false for an unknown path that should render the 404 view. */
	readonly matched: boolean;
}

function matchRoute(url: string): CurrentRoute {
	const pathname = url.split("?")[0];
	if (pathname === "/") {
		return { name: undefined, matched: true };
	}
	const params = exec(pathname, DASHBOARD_ROUTE, {});
	if (params && typeof params.name === "string") {
		return { name: params.name, matched: true };
	}
	return { name: undefined, matched: false };
}

/**
 * Resolves the active dashboard route from the current preact-router URL. Called
 * from the `<Router>`-hosted shell, which re-renders on every navigation, so the
 * value stays current without an extra subscription. Returns the decoded
 * `/dashboards/:name`, treats `/` as the (to-be-normalized) default, and flags
 * any other path as unmatched so the 404 view renders.
 */
export function useCurrentRoute(): CurrentRoute {
	return matchRoute(getCurrentUrl());
}

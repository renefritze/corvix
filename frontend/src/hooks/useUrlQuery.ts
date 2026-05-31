import { route } from "preact-router";

/**
 * Helpers for reading and writing filter/sort state in the URL query string so
 * a filtered/sorted view is shareable. Reads come straight from
 * `window.location` (the actual source of truth, kept current by the browser on
 * Back/Forward) and writes go through preact-router's {@link route}, which keeps
 * the mounted `<Router>` in sync and re-renders the route.
 */

/** Parses the query string of the current URL into URLSearchParams. */
export function currentQuery(): URLSearchParams {
	if (globalThis.window === undefined) {
		return new URLSearchParams("");
	}
	return new URLSearchParams(globalThis.window.location.search);
}

/** Returns the current pathname (without query). */
function currentPathname(): string {
	if (globalThis.window === undefined) {
		return "/";
	}
	return globalThis.window.location.pathname;
}

/** Returns the current `pathname + search`, the full relative URL. */
function currentRelativeUrl(): string {
	if (globalThis.window === undefined) {
		return "/";
	}
	return `${globalThis.window.location.pathname}${globalThis.window.location.search}`;
}

/**
 * Applies `updates` to the current query string and navigates (replacing the
 * history entry so rapid filter/sort changes don't spam history). Keys set to
 * an empty string or `null` are removed.
 */
export function updateQuery(updates: Record<string, string | null>): void {
	const params = currentQuery();
	for (const [key, value] of Object.entries(updates)) {
		if (value === null || value === "") {
			params.delete(key);
		} else {
			params.set(key, value);
		}
	}
	const search = params.toString();
	const nextUrl = `${currentPathname()}${search ? `?${search}` : ""}`;
	// Skip the navigation when nothing changed so we don't trigger a redundant
	// router re-render for a no-op update.
	if (nextUrl !== currentRelativeUrl()) {
		route(nextUrl, true);
	}
}

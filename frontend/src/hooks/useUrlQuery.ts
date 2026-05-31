import { getCurrentUrl, route } from "preact-router";

/**
 * Helpers for reading and writing filter/sort state in the URL query string so
 * a filtered/sorted view is shareable. Built on preact-router's
 * {@link getCurrentUrl} (current location) and {@link route} (navigation).
 */

/** Parses the query string of the current URL into URLSearchParams. */
export function currentQuery(): URLSearchParams {
	const url = getCurrentUrl();
	const index = url.indexOf("?");
	return new URLSearchParams(index === -1 ? "" : url.slice(index + 1));
}

/** Returns the current pathname (without query) from the router URL. */
function currentPathname(): string {
	const url = getCurrentUrl();
	const index = url.indexOf("?");
	return index === -1 ? url : url.slice(0, index);
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
	route(`${currentPathname()}${search ? `?${search}` : ""}`, true);
}

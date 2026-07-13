/**
 * Hand-rolled router — the single reactive source of truth for URL state.
 *
 * `pathname`/`search` are `$state` kept current on `popstate` and on every
 * internal {@link Router.navigate}. `route` derives the matched dashboard from
 * the pathname. `updateQuery` ports the delete-on-empty / replace semantics
 * from the old `useUrlQuery.ts` so filter/sort views stay shareable and
 * Back/Forward-aware without a routing dependency.
 */

export interface RouteMatch {
	/** Decoded dashboard name when on `/dashboards/:name`, else undefined. */
	readonly name: string | undefined;
	/** True for `/` and `/dashboards/:name`; false for anything else (404). */
	readonly matched: boolean;
}

const DASHBOARD_RE = /^\/dashboards\/([^/]+)\/?$/;

function matchRoute(pathname: string): RouteMatch {
	if (pathname === "/") {
		return { name: undefined, matched: true };
	}
	const match = DASHBOARD_RE.exec(pathname);
	if (match) {
		try {
			return { name: decodeURIComponent(match[1]), matched: true };
		} catch {
			return { name: match[1], matched: true };
		}
	}
	return { name: undefined, matched: false };
}

export class Router {
	pathname = $state("/");
	search = $state("");
	#cleanup: (() => void) | null = null;

	constructor() {
		if (globalThis.window !== undefined) {
			this.pathname = globalThis.window.location.pathname;
			this.search = globalThis.window.location.search;
			const onPopState = () => this.#syncFromLocation();
			globalThis.window.addEventListener("popstate", onPopState);
			this.#cleanup = () =>
				globalThis.window.removeEventListener("popstate", onPopState);
		}
	}

	#syncFromLocation(): void {
		this.pathname = globalThis.window.location.pathname;
		this.search = globalThis.window.location.search;
	}

	get route(): RouteMatch {
		return matchRoute(this.pathname);
	}

	/** Parsed query string of the current URL. */
	get query(): URLSearchParams {
		return new URLSearchParams(this.search);
	}

	/** Full relative URL (`pathname` + `search`). */
	get relativeUrl(): string {
		return `${this.pathname}${this.search}`;
	}

	navigate(url: string, replace = false): void {
		if (globalThis.window === undefined) return;
		if (replace) {
			globalThis.window.history.replaceState({}, "", url);
		} else {
			globalThis.window.history.pushState({}, "", url);
		}
		this.#syncFromLocation();
	}

	/**
	 * Applies `updates` to the query string and navigates (replacing history so
	 * rapid filter/sort changes don't spam it). Keys set to `""`/`null` are
	 * removed. No-ops when the resulting URL is unchanged.
	 */
	updateQuery(updates: Record<string, string | null>): void {
		const params = this.query;
		for (const [key, value] of Object.entries(updates)) {
			if (value === null || value === "") {
				params.delete(key);
			} else {
				params.set(key, value);
			}
		}
		const search = params.toString();
		const query = search ? `?${search}` : "";
		const nextUrl = `${this.pathname}${query}`;
		if (nextUrl !== this.relativeUrl) {
			this.navigate(nextUrl, true);
		}
	}

	destroy(): void {
		this.#cleanup?.();
		this.#cleanup = null;
	}
}

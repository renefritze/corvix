/**
 * Filter state with the URL query string as the single source of truth, ported
 * from `useFilters.ts`. Reads are computed from the router query (reactive via
 * the router's `search` state); writes go back through `updateQuery`.
 */
import type { Router } from "./router.svelte";
import type { FilterState } from "../types";

const DEFAULT: FilterState = { unread: "all", reason: [], repository: "" };

const UNREAD_VALUES: ReadonlySet<FilterState["unread"]> = new Set([
	"all",
	"unread",
	"read",
]);

function filtersToQuery(filters: FilterState): Record<string, string | null> {
	return {
		unread: filters.unread === DEFAULT.unread ? null : filters.unread,
		reason: filters.reason.length > 0 ? filters.reason.join(",") : null,
		repository: filters.repository || null,
	};
}

export class FiltersStore {
	#router: Router;

	constructor(router: Router) {
		this.#router = router;
	}

	get filters(): FilterState {
		const params = this.#router.query;
		const unread = params.get("unread");
		const reason = params.get("reason");
		const repository = params.get("repository");
		return {
			unread: UNREAD_VALUES.has(unread as FilterState["unread"])
				? (unread as FilterState["unread"])
				: DEFAULT.unread,
			reason: reason ? reason.split(",").filter(Boolean) : DEFAULT.reason,
			repository: repository ?? DEFAULT.repository,
		};
	}

	setFilter = <K extends keyof FilterState>(
		key: K,
		value: FilterState[K],
	): void => {
		this.#router.updateQuery(filtersToQuery({ ...this.filters, [key]: value }));
	};

	clearFilters = (): void => {
		this.#router.updateQuery(filtersToQuery(DEFAULT));
	};
}

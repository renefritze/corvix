/**
 * Free-text search over title / repository / reason / type, stored as the `q`
 * URL param so a searched view is shareable (new in the rewrite). The router
 * query is the source of truth, matching the filter/sort stores.
 */
import type { Router } from "./router.svelte";
import type { DashboardItem } from "../types";

export class SearchStore {
	#router: Router;

	constructor(router: Router) {
		this.#router = router;
	}

	get query(): string {
		return this.#router.query.get("q") ?? "";
	}

	setQuery = (value: string): void => {
		this.#router.updateQuery({ q: value });
	};

	clear = (): void => {
		this.#router.updateQuery({ q: null });
	};

	matches(item: DashboardItem): boolean {
		const needle = this.query.trim().toLowerCase();
		if (!needle) return true;
		return [
			item.subject_title,
			item.repository,
			item.reason,
			item.subject_type,
		].some((field) => field.toLowerCase().includes(needle));
	}
}

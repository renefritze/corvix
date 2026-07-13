/**
 * Combines filter + sort state, seeding the sort from the snapshot's configured
 * order and locking the unread filter to "unread" when the active dashboard
 * excludes read notifications. Ported from `useFilterSort.ts`.
 */
import { FiltersStore } from "./filters.svelte";
import type { Router } from "./router.svelte";
import { SortStore } from "./sort.svelte";
import type { FilterState, SnapshotPayload, SortColumn } from "../types";

function mapDashboardSortToColumn(sortBy: string): SortColumn {
	if (sortBy === "title") return "subject_title";
	if (sortBy === "repository") return "repository";
	if (sortBy === "subject_type") return "subject_type";
	if (sortBy === "reason") return "reason";
	if (sortBy === "updated_at") return "updated_at";
	return "score";
}

export class FilterSortStore {
	#getSnapshot: () => SnapshotPayload | null;
	filters: FiltersStore;
	sort: SortStore;

	constructor(router: Router, getSnapshot: () => SnapshotPayload | null) {
		this.#getSnapshot = getSnapshot;
		this.filters = new FiltersStore(router);
		this.sort = new SortStore(
			router,
			() => mapDashboardSortToColumn(getSnapshot()?.sort_by ?? "score"),
			() => (getSnapshot()?.descending === false ? "asc" : "desc"),
		);
	}

	get filterState(): FilterState {
		return this.filters.filters;
	}

	setFilter = <K extends keyof FilterState>(
		key: K,
		value: FilterState[K],
	): void => {
		this.filters.setFilter(key, value);
	};

	clearFilters = (): void => {
		this.filters.clearFilters();
	};

	get sortColumn(): SortColumn {
		return this.sort.sortColumn;
	}

	get sortDirection(): "asc" | "desc" {
		return this.sort.sortDirection;
	}

	handleSort = (col: SortColumn): void => {
		this.sort.handleSort(col);
	};

	get dashboardAllowsRead(): boolean {
		return this.#getSnapshot()?.include_read ?? true;
	}

	get effectiveUnreadFilter(): FilterState["unread"] {
		const unread = this.filterState.unread;
		return this.dashboardAllowsRead || unread === "unread" ? unread : "unread";
	}
}

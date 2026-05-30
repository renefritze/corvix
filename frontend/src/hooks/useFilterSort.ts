import { useMemo } from "preact/hooks";
import type { SnapshotPayload, SortColumn } from "../types";
import { useFilters } from "./useFilters";
import { useSort } from "./useSort";

function mapDashboardSortToColumn(sortBy: string): SortColumn {
	if (sortBy === "title") return "subject_title";
	if (sortBy === "repository") return "repository";
	if (sortBy === "subject_type") return "subject_type";
	if (sortBy === "reason") return "reason";
	if (sortBy === "updated_at") return "updated_at";
	return "score";
}

/**
 * Combines filter and sort state, seeding the sort from the snapshot's
 * configured order and locking the unread filter to "unread" when the active
 * dashboard excludes read notifications.
 */
export function useFilterSort(snapshot: SnapshotPayload | null) {
	const { filters, setFilter, clearFilters } = useFilters();

	const configuredSortColumn = useMemo(
		() => mapDashboardSortToColumn(snapshot?.sort_by ?? "score"),
		[snapshot?.sort_by],
	);
	const configuredSortDirection =
		snapshot?.descending === false ? "asc" : "desc";
	const { sortColumn, sortDirection, handleSort } = useSort(
		configuredSortColumn,
		configuredSortDirection,
	);

	const dashboardAllowsRead = snapshot?.include_read ?? true;
	const effectiveUnreadFilter =
		dashboardAllowsRead || filters.unread === "unread"
			? filters.unread
			: "unread";

	return {
		filters,
		setFilter,
		clearFilters,
		sortColumn,
		sortDirection,
		handleSort,
		dashboardAllowsRead,
		effectiveUnreadFilter,
	};
}

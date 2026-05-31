import { useCallback, useState } from "preact/hooks";
import type { FilterState } from "../types";
import { currentQuery, updateQuery } from "./useUrlQuery";

const DEFAULT: FilterState = { unread: "all", reason: [], repository: "" };

const UNREAD_VALUES: readonly FilterState["unread"][] = [
	"all",
	"unread",
	"read",
];

/** Reads the initial filter state from the URL query, falling back to defaults. */
function readFiltersFromUrl(): FilterState {
	if (globalThis.window === undefined) {
		return DEFAULT;
	}
	const params = currentQuery();
	const unread = params.get("unread");
	const reason = params.get("reason");
	const repository = params.get("repository");
	return {
		unread: UNREAD_VALUES.includes(unread as FilterState["unread"])
			? (unread as FilterState["unread"])
			: DEFAULT.unread,
		reason: reason ? reason.split(",").filter(Boolean) : DEFAULT.reason,
		repository: repository ?? DEFAULT.repository,
	};
}

/** Serializes filter state to query params, omitting values at their default. */
function filtersToQuery(filters: FilterState): Record<string, string | null> {
	return {
		unread: filters.unread === DEFAULT.unread ? null : filters.unread,
		reason: filters.reason.length > 0 ? filters.reason.join(",") : null,
		repository: filters.repository || null,
	};
}

/**
 * Owns the filter state and mirrors it into the URL query string so a filtered
 * view can be shared by URL. Initial state is read from the query on mount.
 */
export function useFilters() {
	const [filters, setFilters] = useState<FilterState>(readFiltersFromUrl);

	const setFilter = useCallback(
		<K extends keyof FilterState>(key: K, value: FilterState[K]) => {
			setFilters((prev) => {
				const next = { ...prev, [key]: value };
				updateQuery(filtersToQuery(next));
				return next;
			});
		},
		[],
	);

	const clearFilters = useCallback(() => {
		setFilters(DEFAULT);
		updateQuery(filtersToQuery(DEFAULT));
	}, []);

	return { filters, setFilter, clearFilters };
}

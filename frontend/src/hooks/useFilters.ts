import { useCallback } from "preact/hooks";
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
 * Exposes the filter state with the URL query string as the single source of
 * truth so a filtered view can be shared by URL and browser Back/Forward
 * navigation stays in sync. The filters are read from the query on every render
 * (preact-router re-renders the hosting route on any navigation), and changes
 * are written straight back to the query.
 */
export function useFilters() {
	const filters = readFiltersFromUrl();

	const setFilter = useCallback(
		<K extends keyof FilterState>(key: K, value: FilterState[K]) => {
			updateQuery(filtersToQuery({ ...filters, [key]: value }));
		},
		[filters],
	);

	const clearFilters = useCallback(() => {
		updateQuery(filtersToQuery(DEFAULT));
	}, []);

	return { filters, setFilter, clearFilters };
}

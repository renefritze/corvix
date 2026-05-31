import { useCallback } from "preact/hooks";
import type { SortColumn, SortDirection } from "../types";
import { currentQuery, updateQuery } from "./useUrlQuery";

const SORT_COLUMNS: readonly SortColumn[] = [
	"subject_title",
	"repository",
	"subject_type",
	"reason",
	"updated_at",
	"score",
];

/** Reads a SortColumn from the URL query, or undefined when absent/invalid. */
function readColumnFromUrl(): SortColumn | undefined {
	if (globalThis.window === undefined) {
		return undefined;
	}
	const sort = currentQuery().get("sort");
	return SORT_COLUMNS.includes(sort as SortColumn)
		? (sort as SortColumn)
		: undefined;
}

/** Reads a SortDirection from the URL query, or undefined when absent/invalid. */
function readDirectionFromUrl(): SortDirection | undefined {
	if (globalThis.window === undefined) {
		return undefined;
	}
	const dir = currentQuery().get("dir");
	return dir === "asc" || dir === "desc" ? dir : undefined;
}

/**
 * Exposes sort state with the URL query string as the single source of truth.
 * An explicit `sort`/`dir` query overrides the dashboard's configured order
 * (which seeds the default when the query is absent), and because preact-router
 * re-renders the hosting route on navigation, reading the query each render
 * keeps the UI in sync — including browser Back/Forward. Changes are written
 * straight back to the query so a sorted view can be shared.
 */
export function useSort(
	initialColumn: SortColumn = "score",
	initialDir: SortDirection = "desc",
) {
	const sortColumn = readColumnFromUrl() ?? initialColumn;
	const sortDirection = readDirectionFromUrl() ?? initialDir;

	const handleSort = useCallback(
		(col: SortColumn) => {
			const nextDir =
				col === sortColumn
					? sortDirection === "asc"
						? "desc"
						: "asc"
					: "desc";
			updateQuery({ sort: col, dir: nextDir });
		},
		[sortColumn, sortDirection],
	);

	return { sortColumn, sortDirection, handleSort };
}

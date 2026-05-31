import { useCallback, useEffect, useRef, useState } from "preact/hooks";
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
 * Owns sort state, seeding it from the dashboard's configured order while
 * letting an explicit `sort`/`dir` URL query override that default. Changes are
 * mirrored back into the query string so a sorted view can be shared.
 */
export function useSort(
	initialColumn: SortColumn = "score",
	initialDir: SortDirection = "desc",
) {
	const urlColumn = readColumnFromUrl();
	const urlDir = readDirectionFromUrl();
	const [sortColumn, setSortColumn] = useState<SortColumn>(
		urlColumn ?? initialColumn,
	);
	const [sortDirection, setSortDirection] = useState<SortDirection>(
		urlDir ?? initialDir,
	);
	// True when an explicit sort/dir query param seeded the initial state, in
	// which case the dashboard's configured order must not override the shared
	// URL. User sorts (handleSort) leave this alone, preserving the existing
	// re-seed-on-dashboard-change behaviour.
	const urlControlled = useRef(urlColumn !== undefined || urlDir !== undefined);
	// Latest values for the stable handleSort callback to read without
	// re-subscribing.
	const stateRef = useRef({ column: sortColumn, direction: sortDirection });
	stateRef.current = { column: sortColumn, direction: sortDirection };

	useEffect(() => {
		if (urlControlled.current) {
			return;
		}
		setSortColumn(initialColumn);
		setSortDirection(initialDir);
	}, [initialColumn, initialDir]);

	const handleSort = useCallback((col: SortColumn) => {
		const { column, direction } = stateRef.current;
		const nextDir =
			col === column ? (direction === "asc" ? "desc" : "asc") : "desc";
		setSortColumn(col);
		setSortDirection(nextDir);
		updateQuery({ sort: col, dir: nextDir });
	}, []);

	return { sortColumn, sortDirection, handleSort };
}

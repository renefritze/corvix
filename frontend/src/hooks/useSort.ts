import { useCallback, useEffect, useState } from "preact/hooks";
import type { SortColumn, SortDirection } from "../types";

export function useSort(
	initialColumn: SortColumn = "score",
	initialDir: SortDirection = "desc",
) {
	const [sortColumn, setSortColumn] = useState<SortColumn>(initialColumn);
	const [sortDirection, setSortDirection] = useState<SortDirection>(initialDir);

	useEffect(() => {
		setSortColumn(initialColumn);
		setSortDirection(initialDir);
	}, [initialColumn, initialDir]);

	const handleSort = useCallback(
		(col: SortColumn) => {
			if (col === sortColumn) {
				setSortDirection((d) => (d === "asc" ? "desc" : "asc"));
			} else {
				setSortColumn(col);
				setSortDirection("desc");
			}
		},
		[sortColumn],
	);

	return { sortColumn, sortDirection, handleSort };
}

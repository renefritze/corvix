import { useCallback, useState } from "preact/hooks";
import type { FilterState } from "../types";

const DEFAULT: FilterState = { unread: "all", reason: "", repository: "" };

export function useFilters() {
	const [filters, setFilters] = useState<FilterState>(DEFAULT);

	const setFilter = useCallback(
		<K extends keyof FilterState>(key: K, value: FilterState[K]) => {
			setFilters((prev) => ({ ...prev, [key]: value }));
		},
		[],
	);

	const clearFilters = useCallback(() => setFilters(DEFAULT), []);

	return { filters, setFilter, clearFilters };
}

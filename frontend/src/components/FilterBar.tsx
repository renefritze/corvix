import type { DashboardItem, FilterState } from "../types";

interface FilterBarProps {
	readonly filters: FilterState;
	readonly includeRead: boolean;
	readonly items: DashboardItem[];
	readonly onFilterChange: <K extends keyof FilterState>(
		key: K,
		value: FilterState[K],
	) => void;
	readonly onClearFilters: () => void;
	readonly generatedAt: string | null;
	readonly filterBarRef?: { current: HTMLSelectElement | null };
}

export function FilterBar({
	filters,
	includeRead,
	items,
	onFilterChange,
	onClearFilters,
	generatedAt,
	filterBarRef,
}: FilterBarProps) {
	const reasons = Array.from(new Set(items.map((i) => i.reason))).sort((a, b) =>
		a.localeCompare(b),
	);
	const repositories = Array.from(new Set(items.map((i) => i.repository))).sort(
		(a, b) => a.localeCompare(b),
	);
	const selectedRepositoryMissing =
		filters.repository !== "" && !repositories.includes(filters.repository);
	const selectedRepositoryLabel =
		filters.unread === "unread"
			? `${filters.repository} (no unread notifications)`
			: `${filters.repository} (no matching notifications)`;

	return (
		<div class="filter-row">
			<select
				ref={filterBarRef}
				value={filters.unread}
				onChange={(e) =>
					onFilterChange(
						"unread",
						(e.target as HTMLSelectElement).value as FilterState["unread"],
					)
				}
				aria-label="Unread state filter"
			>
				<option value="all" disabled={!includeRead}>
					{includeRead ? "All" : "🔒 All (disabled by dashboard)"}
				</option>
				<option value="unread">Unread only</option>
				<option value="read" disabled={!includeRead}>
					{includeRead ? "Read only" : "🔒 Read only (disabled by dashboard)"}
				</option>
			</select>
			<select
				value={filters.reason}
				onChange={(e) =>
					onFilterChange("reason", (e.target as HTMLSelectElement).value)
				}
				aria-label="Reason filter"
			>
				<option value="">All reasons</option>
				{reasons.map((r) => (
					<option key={r} value={r}>
						{r}
					</option>
				))}
			</select>
			<select
				value={filters.repository}
				onChange={(e) =>
					onFilterChange("repository", (e.target as HTMLSelectElement).value)
				}
				aria-label="Repository filter"
			>
				<option value="">All repositories</option>
				{selectedRepositoryMissing && (
					<option value={filters.repository}>{selectedRepositoryLabel}</option>
				)}
				{repositories.map((r) => (
					<option key={r} value={r}>
						{r}
					</option>
				))}
			</select>
			<button type="button" onClick={onClearFilters}>
				Clear
			</button>
			{generatedAt && (
				<span class="snapshot-time">
					Snapshot: {new Date(generatedAt).toLocaleTimeString()}
				</span>
			)}
		</div>
	);
}

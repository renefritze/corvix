import type { FilterState, DashboardItem } from "../types";

interface FilterBarProps {
  filters: FilterState;
  items: DashboardItem[];
  onFilterChange: <K extends keyof FilterState>(key: K, value: FilterState[K]) => void;
  onClearFilters: () => void;
  generatedAt: string | null;
  filterBarRef?: { current: HTMLSelectElement | null };
}

export function FilterBar({ filters, items, onFilterChange, onClearFilters, generatedAt, filterBarRef }: FilterBarProps) {
  const reasons = Array.from(new Set(items.map((i) => i.reason))).sort();
  const repositories = Array.from(new Set(items.map((i) => i.repository))).sort();

  return (
    <div class="filter-row">
      <select
        ref={filterBarRef}
        value={filters.unread}
        onChange={(e) => onFilterChange("unread", (e.target as HTMLSelectElement).value as FilterState["unread"])}
        aria-label="Unread state filter"
      >
        <option value="all">All</option>
        <option value="unread">Unread only</option>
        <option value="read">Read only</option>
      </select>
      <select
        value={filters.reason}
        onChange={(e) => onFilterChange("reason", (e.target as HTMLSelectElement).value)}
        aria-label="Reason filter"
      >
        <option value="">All reasons</option>
        {reasons.map((r) => <option key={r} value={r}>{r}</option>)}
      </select>
      <select
        value={filters.repository}
        onChange={(e) => onFilterChange("repository", (e.target as HTMLSelectElement).value)}
        aria-label="Repository filter"
      >
        <option value="">All repositories</option>
        {repositories.map((r) => <option key={r} value={r}>{r}</option>)}
      </select>
      <button type="button" onClick={onClearFilters}>Clear</button>
      {generatedAt && (
        <span class="snapshot-time">
          Snapshot: {new Date(generatedAt).toLocaleTimeString()}
        </span>
      )}
    </div>
  );
}

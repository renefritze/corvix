import type { SortColumn, SortDirection } from "../types";

const COLUMNS: { key: SortColumn; label: string; className?: string }[] = [
	{ key: "subject_title", label: "Title" },
	{ key: "repository", label: "Repository" },
	{ key: "subject_type", label: "Type", className: "hide-mobile" },
	{ key: "reason", label: "Reason", className: "hide-mobile" },
	{ key: "score", label: "Score" },
	{ key: "updated_at", label: "Updated" },
];

interface TableHeaderProps {
	sortColumn: SortColumn;
	sortDirection: SortDirection;
	onSort: (col: SortColumn) => void;
}

export function TableHeader({
	sortColumn,
	sortDirection,
	onSort,
}: TableHeaderProps) {
	return (
		<thead>
			<tr>
				<th class="col-status" aria-label="Unread status" />
				{COLUMNS.map(({ key, label, className }) => (
					<th
						key={key}
						class={[
							className,
							"sortable",
							sortColumn === key ? "sort-active" : "",
						]
							.filter(Boolean)
							.join(" ")}
						aria-sort={
							sortColumn === key
								? sortDirection === "asc"
									? "ascending"
									: "descending"
								: "none"
						}
					>
						<button type="button" onClick={() => onSort(key)}>
							{label}
							{sortColumn === key && (
								<span class="sort-arrow" aria-hidden="true">
									{sortDirection === "asc" ? " ▲" : " ▼"}
								</span>
							)}
						</button>
					</th>
				))}
				<th class="col-actions" aria-label="Actions" />
			</tr>
		</thead>
	);
}

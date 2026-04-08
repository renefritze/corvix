import type {
	ColumnWidths,
	ResizableSortColumn,
	SortColumn,
	SortDirection,
} from "../types";

const COLUMNS: {
	key: SortColumn;
	label: string;
	className?: string;
	colClass: string;
	resizeKey?: ResizableSortColumn;
}[] = [
	{ key: "subject_title", label: "Title", colClass: "col-title" },
	{
		key: "repository",
		label: "Repository",
		colClass: "col-repository",
		resizeKey: "repository",
	},
	{
		key: "subject_type",
		label: "Type",
		className: "hide-mobile",
		colClass: "col-type",
		resizeKey: "subject_type",
	},
	{
		key: "reason",
		label: "Reason",
		className: "hide-mobile",
		colClass: "col-reason",
		resizeKey: "reason",
	},
	{
		key: "score",
		label: "Score",
		colClass: "col-score",
		resizeKey: "score",
	},
	{
		key: "updated_at",
		label: "Updated",
		colClass: "col-updated",
		resizeKey: "updated_at",
	},
];

interface TableHeaderProps {
	sortColumn: SortColumn;
	sortDirection: SortDirection;
	onSort: (col: SortColumn) => void;
	columnWidths: ColumnWidths;
	onResizeStart: (column: ResizableSortColumn, startX: number) => void;
	onResetColumnWidth: (column: ResizableSortColumn) => void;
}

export function TableHeader({
	sortColumn,
	sortDirection,
	onSort,
	columnWidths,
	onResizeStart,
	onResetColumnWidth,
}: TableHeaderProps) {
	return (
		<thead>
			<tr>
				<th class="col-status" aria-label="Unread status" />
				{COLUMNS.map(({ key, label, className, colClass, resizeKey }) => (
					<th
						key={key}
						class={[
							colClass,
							className,
							"sortable",
							sortColumn === key ? "sort-active" : "",
						]
							.filter(Boolean)
							.join(" ")}
						style={
							resizeKey ? { width: `${columnWidths[resizeKey]}px` } : undefined
						}
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
						{resizeKey && (
							<span
								class="col-resize-handle"
								onMouseDown={(event) => {
									event.preventDefault();
									event.stopPropagation();
									onResizeStart(resizeKey, event.clientX);
								}}
								onDblClick={(event) => {
									event.preventDefault();
									event.stopPropagation();
									onResetColumnWidth(resizeKey);
								}}
							/>
						)}
					</th>
				))}
				<th class="col-actions" aria-label="Actions" />
			</tr>
		</thead>
	);
}

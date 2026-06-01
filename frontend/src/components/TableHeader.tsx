import type {
	ColumnWidths,
	ResizableSortColumn,
	SortColumn,
	SortDirection,
} from "../types";
import styles from "./table.module.css";

const COLUMNS: {
	key: SortColumn;
	label: string;
	extraClass?: string;
	colClass: string;
	resizeKey?: ResizableSortColumn;
}[] = [
	{ key: "subject_title", label: "Title", colClass: styles.colTitle },
	{
		key: "repository",
		label: "Repository",
		colClass: styles.colRepository,
		resizeKey: "repository",
	},
	{
		key: "subject_type",
		label: "Type",
		extraClass: styles.hideMobile,
		colClass: styles.colType,
		resizeKey: "subject_type",
	},
	{
		key: "reason",
		label: "Reason",
		extraClass: styles.hideMobile,
		colClass: styles.colReason,
		resizeKey: "reason",
	},
	{
		key: "score",
		label: "Score",
		colClass: styles.colScore,
		resizeKey: "score",
	},
	{
		key: "updated_at",
		label: "Updated",
		colClass: styles.colUpdated,
		resizeKey: "updated_at",
	},
];

interface TableHeaderProps {
	readonly sortColumn: SortColumn;
	readonly sortDirection: SortDirection;
	readonly onSort: (col: SortColumn) => void;
	readonly columnWidths: ColumnWidths;
	readonly onResizeStart: (column: ResizableSortColumn, startX: number) => void;
	readonly onResetColumnWidth: (column: ResizableSortColumn) => void;
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
				<th class={styles.colStatus} aria-label="Unread status" />
				{COLUMNS.map(({ key, label, extraClass, colClass, resizeKey }) => {
					let ariaSort: "none" | "ascending" | "descending" = "none";
					if (sortColumn === key) {
						ariaSort = sortDirection === "asc" ? "ascending" : "descending";
					}

					return (
						<th
							key={key}
							class={[
								colClass,
								extraClass,
								styles.sortable,
								sortColumn === key ? styles.sortActive : "",
							]
								.filter(Boolean)
								.join(" ")}
							style={
								resizeKey
									? { width: `${columnWidths[resizeKey]}px` }
									: undefined
							}
							aria-sort={ariaSort}
						>
							<button type="button" onClick={() => onSort(key)}>
								{label}
								{sortColumn === key && (
									<span class={styles.sortArrow} aria-hidden="true">
										{sortDirection === "asc" ? " ▲" : " ▼"}
									</span>
								)}
							</button>
							{resizeKey && (
								<button
									type="button"
									class={styles.colResizeHandle}
									aria-label={`Resize ${label} column`}
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
					);
				})}
				<th class={styles.colActions} aria-label="Actions" />
			</tr>
		</thead>
	);
}

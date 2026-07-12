<script lang="ts">
	import type {
		ColumnWidths,
		ResizableSortColumn,
		SortColumn,
		SortDirection,
	} from "../types";

	interface Column {
		key: SortColumn;
		label: string;
		colClass: string;
		extraClass?: string;
		resizeKey?: ResizableSortColumn;
	}

	const COLUMNS: Column[] = [
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
			colClass: "col-type",
			extraClass: "hide-mobile",
			resizeKey: "subject_type",
		},
		{
			key: "reason",
			label: "Reason",
			colClass: "col-reason",
			extraClass: "hide-mobile",
			resizeKey: "reason",
		},
		{ key: "score", label: "Score", colClass: "col-score", resizeKey: "score" },
		{
			key: "updated_at",
			label: "Updated",
			colClass: "col-updated",
			resizeKey: "updated_at",
		},
	];

	interface Props {
		sortColumn: SortColumn;
		sortDirection: SortDirection;
		onSort: (col: SortColumn) => void;
		columnWidths: ColumnWidths;
		onResizeStart: (column: ResizableSortColumn, startX: number) => void;
		onResetColumnWidth: (column: ResizableSortColumn) => void;
	}

	let {
		sortColumn,
		sortDirection,
		onSort,
		columnWidths,
		onResizeStart,
		onResetColumnWidth,
	}: Props = $props();

	function ariaSort(key: SortColumn): "none" | "ascending" | "descending" {
		if (sortColumn !== key) return "none";
		return sortDirection === "asc" ? "ascending" : "descending";
	}
</script>

<thead>
	<tr>
		<th class="col-status" aria-label="Unread status"></th>
		{#each COLUMNS as column (column.key)}
			<th
				class="{column.colClass} {column.extraClass ?? ''} nt-th-sortable"
				class:nt-th-active={sortColumn === column.key}
				style={column.resizeKey
					? `width: ${columnWidths[column.resizeKey]}px`
					: undefined}
				aria-sort={ariaSort(column.key)}
			>
				<button type="button" class="nt-th-button" onclick={() => onSort(column.key)}>
					{column.label}
					{#if sortColumn === column.key}
						<span class="nt-sort-arrow" aria-hidden="true">
							{sortDirection === "asc" ? "▲" : "▼"}
						</span>
					{/if}
				</button>
				{#if column.resizeKey}
					{@const resizeKey = column.resizeKey}
					<button
						type="button"
						class="nt-resize"
						aria-label={`Resize ${column.label} column`}
						onmousedown={(event) => {
							event.preventDefault();
							event.stopPropagation();
							onResizeStart(resizeKey, event.clientX);
						}}
						ondblclick={(event) => {
							event.preventDefault();
							event.stopPropagation();
							onResetColumnWidth(resizeKey);
						}}
					></button>
				{/if}
			</th>
		{/each}
		<th class="col-actions" aria-label="Actions"></th>
	</tr>
</thead>

<script lang="ts">
	import type {
		ColumnWidths,
		DashboardGroup,
		DashboardItem,
		ResizableSortColumn,
		SortColumn,
		SortDirection,
	} from "../types";
	import { notificationKey } from "../types";
	import GroupHeader from "./GroupHeader.svelte";
	import TableHeader from "./TableHeader.svelte";
	import TableRow from "./TableRow.svelte";

	interface Props {
		groups: DashboardGroup[];
		sortColumn: SortColumn;
		sortDirection: SortDirection;
		onSort: (col: SortColumn) => void;
		onDismiss: (accountId: string, threadId: string) => void;
		onDismissGroupRead: (groupName: string, items: DashboardItem[]) => void;
		onMarkGroupRead: (groupName: string, items: DashboardItem[]) => void;
		markingGroupNames: Set<string>;
		onOpenTarget: (accountId: string, threadId: string) => void;
		onRequestIgnoreRule: (
			item: DashboardItem,
			position: { x: number; y: number },
		) => void;
		pendingDismissals: Set<string>;
		columnWidths: ColumnWidths;
		onResizeStart: (column: ResizableSortColumn, startX: number) => void;
		onResetColumnWidth: (column: ResizableSortColumn) => void;
		isCollapsed: (name: string) => boolean;
		onToggleCollapse: (name: string) => void;
	}

	let {
		groups,
		sortColumn,
		sortDirection,
		onSort,
		onDismiss,
		onDismissGroupRead,
		onMarkGroupRead,
		markingGroupNames,
		onOpenTarget,
		onRequestIgnoreRule,
		pendingDismissals,
		columnWidths,
		onResizeStart,
		onResetColumnWidth,
		isCollapsed,
		onToggleCollapse,
	}: Props = $props();

	const COLS = 8;

	function sortItems(
		items: DashboardItem[],
		col: SortColumn,
		dir: SortDirection,
	): DashboardItem[] {
		const sorted = [...items].sort((a, b) => {
			const valueA = a[col];
			const valueB = b[col];
			if (typeof valueA === "string" && typeof valueB === "string") {
				const normalizedA = valueA.toLowerCase();
				const normalizedB = valueB.toLowerCase();
				if (normalizedA < normalizedB) return -1;
				if (normalizedA > normalizedB) return 1;
				return 0;
			}
			if (valueA < valueB) return -1;
			if (valueA > valueB) return 1;
			return 0;
		});
		return dir === "desc" ? sorted.reverse() : sorted;
	}
</script>

<table class="nt-table" aria-label="Notifications">
	<caption class="nt-caption">Press ? for keyboard shortcuts</caption>
	<TableHeader
		{sortColumn}
		{sortDirection}
		{onSort}
		{columnWidths}
		{onResizeStart}
		{onResetColumnWidth}
	/>
	<tbody>
		{#each groups as group (group.name)}
			{@const unreadCount = group.items.filter((item) => item.unread).length}
			{@const readCount = group.items.length - unreadCount}
			{@const collapsed = isCollapsed(group.name)}
			{@const isDismissingGroup = group.items.some(
				(item) => !item.unread && pendingDismissals.has(notificationKey(item)),
			)}
			<GroupHeader
				name={group.name}
				total={group.items.length}
				{unreadCount}
				{readCount}
				isMarkingRead={markingGroupNames.has(group.name)}
				{isDismissingGroup}
				{collapsed}
				colspan={COLS}
				onToggleCollapse={() => onToggleCollapse(group.name)}
				onMarkAllRead={() => onMarkGroupRead(group.name, group.items)}
				onRemoveRead={() => onDismissGroupRead(group.name, group.items)}
			/>
			{#if !collapsed}
				{#each sortItems(group.items, sortColumn, sortDirection) as item (notificationKey(item))}
					<TableRow
						{item}
						{onDismiss}
						{onOpenTarget}
						{onRequestIgnoreRule}
						isPendingDismissal={pendingDismissals.has(notificationKey(item))}
					/>
				{/each}
			{/if}
		{/each}
	</tbody>
</table>

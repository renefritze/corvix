import { useColumnResize } from "../hooks/useColumnResize";
import type {
	DashboardGroup,
	DashboardItem,
	SortColumn,
	SortDirection,
} from "../types";
import { notificationKey } from "../types";
import { TableHeader } from "./TableHeader";
import { TableRow } from "./TableRow";
import styles from "./table.module.css";

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

interface NotificationTableProps {
	readonly groups: DashboardGroup[];
	readonly sortColumn: SortColumn;
	readonly sortDirection: SortDirection;
	readonly onSort: (col: SortColumn) => void;
	readonly onDismiss: (accountId: string, threadId: string) => void;
	readonly onMarkGroupRead: (groupName: string, items: DashboardItem[]) => void;
	readonly markingGroupNames: Set<string>;
	readonly onOpenTarget: (accountId: string, threadId: string) => void;
	readonly onRequestIgnoreRule: (
		item: DashboardItem,
		position: { x: number; y: number },
	) => void;
	readonly pendingDismissals: Set<string>;
}

export function NotificationTable({
	groups,
	sortColumn,
	sortDirection,
	onSort,
	onDismiss,
	onMarkGroupRead,
	markingGroupNames,
	onOpenTarget,
	onRequestIgnoreRule,
	pendingDismissals,
}: NotificationTableProps) {
	const COLS = 8;
	const { widths, startResize, resetColumnWidth } = useColumnResize();

	return (
		<table class={styles.notificationTable} aria-label="Notifications">
			<caption class={styles.tableShortcutHint}>
				Press ? for keyboard shortcuts
			</caption>
			<TableHeader
				sortColumn={sortColumn}
				sortDirection={sortDirection}
				onSort={onSort}
				columnWidths={widths}
				onResizeStart={startResize}
				onResetColumnWidth={resetColumnWidth}
			/>
			<tbody>
				{groups.map((group) => {
					const sorted = sortItems(group.items, sortColumn, sortDirection);
					const unreadCount = group.items.filter((item) => item.unread).length;
					const isMarkingRead = markingGroupNames.has(group.name);
					return [
						<tr key={`group-${group.name}`} class={styles.groupHeaderRow} data-testid="group-header-row">
							<td colSpan={COLS} class="group-header-cell">
								<div class={styles.groupHeaderContent}>
									<div>
										{group.name}{" "}
										<span class={styles.groupCount}>({group.items.length})</span>
									</div>
									{unreadCount > 0 && (
										<button
											type="button"
											class={styles.groupMarkReadBtn}
											onClick={() => onMarkGroupRead(group.name, group.items)}
											disabled={isMarkingRead}
											aria-label={`Mark all visible unread notifications in ${group.name} as read`}
										>
											{isMarkingRead
												? "Marking..."
												: `Mark all read (${unreadCount})`}
										</button>
									)}
								</div>
							</td>
						</tr>,
						...sorted.map((item) => (
							<TableRow
								key={notificationKey(item)}
								item={item}
								onDismiss={onDismiss}
								onOpenTarget={onOpenTarget}
								onRequestIgnoreRule={onRequestIgnoreRule}
								isPendingDismissal={pendingDismissals.has(
									notificationKey(item),
								)}
							/>
						)),
					];
				})}
			</tbody>
		</table>
	);
}

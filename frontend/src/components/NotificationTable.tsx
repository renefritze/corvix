import type {
	DashboardGroup,
	DashboardItem,
	SortColumn,
	SortDirection,
} from "../types";
import { TableHeader } from "./TableHeader";
import { TableRow } from "./TableRow";

function sortItems(
	items: DashboardItem[],
	col: SortColumn,
	dir: SortDirection,
): DashboardItem[] {
	const sorted = [...items].sort((a, b) => {
		let av: string | number = a[col] as string | number;
		let bv: string | number = b[col] as string | number;
		if (typeof av === "string" && typeof bv === "string") {
			av = av.toLowerCase();
			bv = bv.toLowerCase();
		}
		if (av < bv) return -1;
		if (av > bv) return 1;
		return 0;
	});
	return dir === "desc" ? sorted.reverse() : sorted;
}

interface NotificationTableProps {
	groups: DashboardGroup[];
	sortColumn: SortColumn;
	sortDirection: SortDirection;
	onSort: (col: SortColumn) => void;
	onDismiss: (threadId: string) => void;
	onOpenTarget: (threadId: string) => void;
	pendingDismissals: Set<string>;
}

export function NotificationTable({
	groups,
	sortColumn,
	sortDirection,
	onSort,
	onDismiss,
	onOpenTarget,
	pendingDismissals,
}: NotificationTableProps) {
	const COLS = 8;
	return (
		<table class="notification-table">
			<TableHeader
				sortColumn={sortColumn}
				sortDirection={sortDirection}
				onSort={onSort}
			/>
			<tbody>
				{groups.map((group) => {
					const sorted = sortItems(group.items, sortColumn, sortDirection);
					return [
						<tr key={`group-${group.name}`} class="group-header-row">
							<td colSpan={COLS} class="group-header-cell">
								{group.name}{" "}
								<span class="group-count">({group.items.length})</span>
							</td>
						</tr>,
						...sorted.map((item) => (
							<TableRow
								key={item.thread_id}
								item={item}
								onDismiss={onDismiss}
								onOpenTarget={onOpenTarget}
								isPendingDismissal={pendingDismissals.has(item.thread_id)}
							/>
						)),
					];
				})}
			</tbody>
		</table>
	);
}

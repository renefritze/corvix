import { useCallback, useMemo, useRef, useState } from "preact/hooks";
import { markNotificationRead } from "./api";
import { EmptyState } from "./components/EmptyState";
import { FilterBar } from "./components/FilterBar";
import { LoadingSkeleton } from "./components/LoadingSkeleton";
import { NotificationTable } from "./components/NotificationTable";
import { Toolbar } from "./components/Toolbar";
import { UndoToast } from "./components/UndoToast";
import { useBrowserNotifications } from "./hooks/useBrowserNotifications";
import { useDismiss } from "./hooks/useDismiss";
import { useFilters } from "./hooks/useFilters";
import { useKeyboard } from "./hooks/useKeyboard";
import { useSnapshot } from "./hooks/useSnapshot";
import { useSort } from "./hooks/useSort";
import type { DashboardItem, FilterState } from "./types";

export function App() {
	const [dashboard, setDashboard] = useState<string | undefined>(undefined);
	const [toastError, setToastError] = useState<string | null>(null);
	const [showShortcuts, setShowShortcuts] = useState(false);
	const filterBarRef = useRef<HTMLSelectElement | null>(null);

	const { snapshot, loading, refreshing, error, refresh } =
		useSnapshot(dashboard);
	const { filters, setFilter, clearFilters } = useFilters();
	const { sortColumn, sortDirection, handleSort } = useSort("score", "desc");
	const { pending, dismiss, undoAll } = useDismiss(refresh, setToastError);

	const allItems = useMemo<DashboardItem[]>(() => {
		if (!snapshot) return [];
		return snapshot.groups.flatMap((g) => g.items);
	}, [snapshot]);

	const notifConfig = snapshot?.notifications_config?.browser_tab ?? null;
	const {
		permission: notifPermission,
		active: notifActive,
		supported: notifSupported,
		enable: enableNotifications,
		disable: disableNotifications,
	} = useBrowserNotifications({
		items: allItems,
		config: notifConfig,
	});

	const filteredGroups = useMemo(() => {
		if (!snapshot) return [];
		return snapshot.groups
			.map((group) => ({
				...group,
				items: group.items.filter((item) => {
					if (pending.has(item.thread_id)) return false;
					if (filters.unread !== "all") {
						if (filters.unread === "unread" && !item.unread) return false;
						if (filters.unread === "read" && item.unread) return false;
					}
					if (filters.reason && item.reason !== filters.reason) return false;
					if (filters.repository && item.repository !== filters.repository)
						return false;
					return true;
				}),
			}))
			.filter((g) => g.items.length > 0);
	}, [snapshot, filters, pending]);

	const hasFilters =
		filters.unread !== "all" ||
		filters.reason !== "" ||
		filters.repository !== "";

	const handleDismissFocused = useCallback(() => {
		const focused = document.activeElement as HTMLElement | null;
		const row = focused?.closest<HTMLTableRowElement>("tr[data-thread-id]");
		const threadId = row?.dataset.threadId;
		if (threadId) dismiss(threadId);
	}, [dismiss]);

	const handleOpenTarget = useCallback(
		(threadId: string) => {
			void markNotificationRead(threadId)
				.then(() => refresh())
				.catch((err: unknown) => {
					setToastError(
						err instanceof Error ? err.message : "Mark read failed",
					);
				});
		},
		[refresh],
	);

	useKeyboard({
		onRefresh: refresh,
		onFocusFilters: () => filterBarRef.current?.focus(),
		onDismissFocused: handleDismissFocused,
		onToggleShortcuts: () => setShowShortcuts((prev) => !prev),
	});

	const dashboardNames = snapshot?.dashboard_names ?? [];
	const currentDashboard = dashboard ?? dashboardNames[0] ?? null;

	return (
		<div class="shell">
			{refreshing && <div class="refresh-bar" aria-hidden="true" />}
			<Toolbar
				dashboardNames={dashboardNames}
				currentDashboard={currentDashboard}
				onDashboardChange={setDashboard}
				onRefresh={refresh}
				refreshing={refreshing}
				summary={snapshot?.summary ?? null}
				shortcutsOpen={showShortcuts}
				onToggleShortcuts={() => setShowShortcuts((prev) => !prev)}
				notifSupported={notifSupported}
				notifActive={notifActive}
				notifPermission={notifPermission}
				onEnableNotifications={() => void enableNotifications()}
				onDisableNotifications={disableNotifications}
			/>
			{showShortcuts && (
				<section
					id="shortcuts-panel"
					class="shortcuts-panel"
					role="dialog"
					aria-label="Keyboard shortcuts"
				>
					<p>Vimium-first shortcuts</p>
					<p>
						<kbd>F</kbd> focus filters, <kbd>R</kbd> refresh, <kbd>J</kbd>
						and <kbd>K</kbd> move between notifications, <kbd>D</kbd>
						dismiss focused notification, <kbd>?</kbd> toggle this panel.
					</p>
				</section>
			)}
			{snapshot && (
				<FilterBar
					filters={filters}
					items={allItems}
					onFilterChange={setFilter}
					onClearFilters={clearFilters}
					generatedAt={snapshot.generated_at}
					filterBarRef={filterBarRef}
				/>
			)}
			<main class="board">
				{loading ? (
					<LoadingSkeleton />
				) : error ? (
					<EmptyState
						hasFilters={false}
						totalItems={0}
						onClearFilters={clearFilters}
						onRetry={refresh}
						error={error}
					/>
				) : filteredGroups.length === 0 ? (
					<EmptyState
						hasFilters={hasFilters}
						totalItems={snapshot?.total_items ?? 0}
						onClearFilters={clearFilters}
						onRetry={refresh}
					/>
				) : (
					<NotificationTable
						groups={filteredGroups}
						sortColumn={sortColumn}
						sortDirection={sortDirection}
						onSort={handleSort}
						onDismiss={dismiss}
						onOpenTarget={handleOpenTarget}
						pendingDismissals={new Set(pending.keys())}
					/>
				)}
			</main>
			{toastError && (
				<div class="error-toast" role="alert">
					{toastError}
					<button type="button" onClick={() => setToastError(null)}>
						✕
					</button>
				</div>
			)}
			<UndoToast count={pending.size} onUndoAll={undoAll} />
		</div>
	);
}

import { Router, getCurrentUrl } from "preact-router";
import type { RoutableProps } from "preact-router";
import { useCallback, useMemo, useRef, useState } from "preact/hooks";
import { AuthProvider } from "./auth/AuthContext";
import { AuthGate } from "./auth/AuthGate";
import { EmptyState } from "./components/EmptyState";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { FilterBar } from "./components/FilterBar";
import { IgnoreRuleDialog } from "./components/IgnoreRuleDialog";
import { LoadingSkeleton } from "./components/LoadingSkeleton";
import { NotFound } from "./components/NotFound";
import { NotificationTable } from "./components/NotificationTable";
import { PollerWarning } from "./components/PollerWarning";
import { Toolbar } from "./components/Toolbar";
import { UndoToast } from "./components/UndoToast";
import { useBrowserNotifications } from "./hooks/useBrowserNotifications";
import { useCurrentRoute } from "./hooks/useCurrentRoute";
import { useDashboardState } from "./hooks/useDashboardState";
import { useDismiss } from "./hooks/useDismiss";
import { useFilterSort } from "./hooks/useFilterSort";
import { useIgnoreRuleDialog } from "./hooks/useIgnoreRuleDialog";
import { useKeyboard } from "./hooks/useKeyboard";
import { useMarkRead } from "./hooks/useMarkRead";
import { notificationKey } from "./types";
import type { DashboardItem } from "./types";

interface DashboardProps {
	// The active dashboard name from the /dashboards/:name route (already decoded).
	readonly name?: string;
}

function Dashboard({ name }: DashboardProps) {
	const [toastError, setToastError] = useState<string | null>(null);
	const [showShortcuts, setShowShortcuts] = useState(false);
	const filterBarRef = useRef<HTMLSelectElement | null>(null);

	const {
		snapshot,
		loading,
		refreshing,
		manualRefreshing,
		error,
		refresh,
		dashboardNames,
		currentDashboard,
		setDashboard,
	} = useDashboardState(name);

	const {
		filters,
		setFilter,
		clearFilters,
		sortColumn,
		sortDirection,
		handleSort,
		dashboardAllowsRead,
		effectiveUnreadFilter,
	} = useFilterSort(snapshot);

	const allItems = useMemo<DashboardItem[]>(() => {
		if (!snapshot) return [];
		return snapshot.groups.flatMap((g) => g.items);
	}, [snapshot]);

	const currentThreadIds = useMemo(
		() => new Set(allItems.map((item) => notificationKey(item))),
		[allItems],
	);

	const { pending, dismiss, undoAll, hiddenThreadIds } = useDismiss(
		refresh,
		setToastError,
		currentThreadIds,
	);
	const hiddenIds = hiddenThreadIds;

	const { markingGroupNames, openTarget, markGroupRead } = useMarkRead(
		refresh,
		setToastError,
	);

	const {
		menu: ignoreMenu,
		dialogItem: ignoreDialogItem,
		snippets: ignoreSnippets,
		loading: ignoreLoading,
		error: ignoreError,
		requestRule: requestIgnoreRule,
		openDialog: openIgnoreDialog,
		closeDialog: closeIgnoreDialog,
	} = useIgnoreRuleDialog(currentDashboard);

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
					if (hiddenIds.has(notificationKey(item))) return false;
					if (effectiveUnreadFilter !== "all") {
						if (effectiveUnreadFilter === "unread" && !item.unread)
							return false;
						if (effectiveUnreadFilter === "read" && item.unread) return false;
					}
					if (
						filters.reason.length > 0 &&
						!filters.reason.includes(item.reason)
					)
						return false;
					if (filters.repository && item.repository !== filters.repository)
						return false;
					return true;
				}),
			}))
			.filter((g) => g.items.length > 0);
	}, [snapshot, filters, hiddenIds, effectiveUnreadFilter]);

	const hasFilters =
		effectiveUnreadFilter !== "all" ||
		filters.reason.length > 0 ||
		filters.repository !== "";

	const handleDismissFocused = useCallback(() => {
		const focused = document.activeElement;
		const row = focused?.closest<HTMLTableRowElement>("tr[data-thread-id]");
		const accountId = row?.dataset.accountId;
		const threadId = row?.dataset.threadId;
		if (accountId && threadId) dismiss(accountId, threadId);
	}, [dismiss]);

	useKeyboard({
		onRefresh: refresh,
		onFocusFilters: () => filterBarRef.current?.focus(),
		onDismissFocused: handleDismissFocused,
		onToggleShortcuts: () => setShowShortcuts((prev) => !prev),
	});

	let boardContent = <LoadingSkeleton />;
	if (!loading) {
		if (error) {
			boardContent = (
				<EmptyState
					hasFilters={false}
					totalItems={0}
					onClearFilters={clearFilters}
					onRetry={refresh}
					error={error}
				/>
			);
		} else if (filteredGroups.length === 0) {
			boardContent = (
				<EmptyState
					hasFilters={hasFilters}
					totalItems={snapshot?.total_items ?? 0}
					onClearFilters={clearFilters}
					onRetry={refresh}
					filterContext={{
						unread: effectiveUnreadFilter,
						reason: filters.reason,
						repository: filters.repository,
					}}
				/>
			);
		} else {
			boardContent = (
				<ErrorBoundary onRetry={refresh}>
					<NotificationTable
						groups={filteredGroups}
						sortColumn={sortColumn}
						sortDirection={sortDirection}
						onSort={handleSort}
						onDismiss={dismiss}
						onMarkGroupRead={markGroupRead}
						markingGroupNames={markingGroupNames}
						onOpenTarget={openTarget}
						onRequestIgnoreRule={requestIgnoreRule}
						pendingDismissals={new Set(pending.keys())}
					/>
				</ErrorBoundary>
			);
		}
	}

	return (
		<div class="shell">
			{refreshing && <div class="refresh-bar" aria-hidden="true" />}
			<Toolbar
				dashboardNames={dashboardNames}
				currentDashboard={currentDashboard}
				onDashboardChange={(name) => setDashboard(name)}
				onRefresh={refresh}
				refreshing={manualRefreshing}
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
				<dialog
					id="shortcuts-panel"
					class="shortcuts-panel"
					aria-label="Keyboard shortcuts"
					open
				>
					<p>Vimium-first shortcuts</p>
					<p>
						<kbd>F</kbd> focus filters, <kbd>R</kbd> refresh, <kbd>J</kbd> and{" "}
						<kbd>K</kbd> move between notifications, <kbd>D</kbd> dismiss
						focused notification, <kbd>?</kbd> toggle this panel.
					</p>
				</dialog>
			)}
			{snapshot && (
				<FilterBar
					filters={{ ...filters, unread: effectiveUnreadFilter }}
					includeRead={dashboardAllowsRead}
					items={allItems}
					onFilterChange={(key, value) => {
						if (
							key === "unread" &&
							!dashboardAllowsRead &&
							value !== "unread"
						) {
							setFilter("unread", "unread");
							return;
						}
						setFilter(key, value);
					}}
					onClearFilters={clearFilters}
					generatedAt={snapshot.generated_at}
					filterBarRef={filterBarRef}
				/>
			)}
			{snapshot?.poller && <PollerWarning poller={snapshot.poller} />}
			<main class="board">{boardContent}</main>
			{ignoreMenu && (
				<div
					class="row-context-menu"
					style={{ left: `${ignoreMenu.x}px`, top: `${ignoreMenu.y}px` }}
					role="menu"
				>
					<button
						type="button"
						role="menuitem"
						onClick={() => openIgnoreDialog(ignoreMenu.item)}
					>
						Create ignore rule...
					</button>
				</div>
			)}
			{ignoreDialogItem !== null && (
				<ErrorBoundary onRetry={closeIgnoreDialog}>
					<IgnoreRuleDialog
						open
						item={ignoreDialogItem}
						dashboardName={currentDashboard}
						snippets={ignoreSnippets}
						loading={ignoreLoading}
						error={ignoreError}
						onClose={closeIgnoreDialog}
					/>
				</ErrorBoundary>
			)}
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

/**
 * Renders the matched route. The root and `/dashboards/:name` paths render the
 * dashboard (normalization to the default dashboard happens in
 * {@link useDashboardState}); anything else renders the in-SPA 404 view. The
 * dashboard stays mounted across `/` -> `/dashboards/:name` normalization so the
 * snapshot is not refetched on a route swap.
 */
function Shell(_props: RoutableProps) {
	const { name, matched } = useCurrentRoute();
	if (!matched) {
		return <NotFound url={getCurrentUrl()} />;
	}
	return <Dashboard name={name} />;
}

/**
 * The single `<Router>` keeps preact-router's navigation primitives ({@link
 * route}, history sync) active while delegating route matching to {@link Shell},
 * so the always-mounted shell can switch between the dashboard and the 404 view
 * without remounting the dashboard on URL normalization.
 */
export function App() {
	return (
		<AuthProvider>
			<AuthGate>
				<Router>
					<Shell default />
				</Router>
			</AuthGate>
		</AuthProvider>
	);
}

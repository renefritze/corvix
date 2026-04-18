import {
	useCallback,
	useEffect,
	useMemo,
	useRef,
	useState,
} from "preact/hooks";
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
import { notificationKey } from "./types";
import type { DashboardItem, SortColumn } from "./types";

const DASHBOARD_PATH_PREFIX = "/dashboards/";

function mapDashboardSortToColumn(sortBy: string): SortColumn {
	if (sortBy === "title") return "subject_title";
	if (sortBy === "repository") return "repository";
	if (sortBy === "subject_type") return "subject_type";
	if (sortBy === "reason") return "reason";
	if (sortBy === "updated_at") return "updated_at";
	return "score";
}

function parseDashboardFromPath(pathname: string): string | undefined {
	if (!pathname.startsWith(DASHBOARD_PATH_PREFIX)) {
		return undefined;
	}
	const rawName = pathname.slice(DASHBOARD_PATH_PREFIX.length);
	if (!rawName) {
		return undefined;
	}
	return decodeURIComponent(rawName);
}

function dashboardPath(name: string | undefined): string {
	if (!name) {
		return "/";
	}
	return `${DASHBOARD_PATH_PREFIX}${encodeURIComponent(name)}`;
}

export function App() {
	const [dashboard, setDashboard] = useState<string | undefined>(() => {
		if (typeof window === "undefined") {
			return undefined;
		}
		return parseDashboardFromPath(window.location.pathname);
	});
	const [toastError, setToastError] = useState<string | null>(null);
	const [showShortcuts, setShowShortcuts] = useState(false);
	const filterBarRef = useRef<HTMLSelectElement | null>(null);

	const { snapshot, loading, refreshing, manualRefreshing, error, refresh } =
		useSnapshot(dashboard);
	const { filters, setFilter, clearFilters } = useFilters();
	const configuredSortColumn = useMemo(
		() => mapDashboardSortToColumn(snapshot?.sort_by ?? "score"),
		[snapshot?.sort_by],
	);
	const configuredSortDirection =
		snapshot?.descending === false ? "asc" : "desc";
	const { sortColumn, sortDirection, handleSort } = useSort(
		configuredSortColumn,
		configuredSortDirection,
	);

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
	const dashboardAllowsRead = snapshot?.include_read ?? true;
	const effectiveUnreadFilter =
		dashboardAllowsRead || filters.unread === "unread"
			? filters.unread
			: "unread";

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
					if (filters.reason && item.reason !== filters.reason) return false;
					if (filters.repository && item.repository !== filters.repository)
						return false;
					return true;
				}),
			}))
			.filter((g) => g.items.length > 0);
	}, [snapshot, filters, hiddenIds, effectiveUnreadFilter]);

	const hasFilters =
		effectiveUnreadFilter !== "all" ||
		filters.reason !== "" ||
		filters.repository !== "";

	const handleDismissFocused = useCallback(() => {
		const focused = document.activeElement as HTMLElement | null;
		const row = focused?.closest<HTMLTableRowElement>("tr[data-thread-id]");
		const accountId = row?.dataset.accountId;
		const threadId = row?.dataset.threadId;
		if (accountId && threadId) dismiss(accountId, threadId);
	}, [dismiss]);

	const handleOpenTarget = useCallback(
		(accountId: string, threadId: string) => {
			void markNotificationRead(accountId, threadId)
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

	useEffect(() => {
		if (typeof window === "undefined") {
			return;
		}
		const handlePopState = () => {
			const fromPath = parseDashboardFromPath(window.location.pathname);
			if (!fromPath) {
				setDashboard(undefined);
				return;
			}
			if (dashboardNames.length > 0 && !dashboardNames.includes(fromPath)) {
				setDashboard(undefined);
				return;
			}
			setDashboard(fromPath);
		};
		window.addEventListener("popstate", handlePopState);
		return () => window.removeEventListener("popstate", handlePopState);
	}, [dashboardNames]);

	useEffect(() => {
		if (typeof window === "undefined") {
			return;
		}
		if (dashboardNames.length === 0) {
			return;
		}
		if (dashboard && !dashboardNames.includes(dashboard)) {
			setDashboard(undefined);
		}
	}, [dashboard, dashboardNames]);

	useEffect(() => {
		if (typeof window === "undefined") {
			return;
		}
		const targetPath = dashboardPath(currentDashboard ?? undefined);
		if (window.location.pathname === targetPath) {
			return;
		}
		window.history.pushState({}, "", targetPath);
	}, [currentDashboard]);

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

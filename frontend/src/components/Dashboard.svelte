<script lang="ts">
	import { BrowserNotificationsStore } from "../lib/browserNotifications.svelte";
	import type { Command } from "../lib/commandPalette.svelte";
	import { CommandPaletteStore } from "../lib/commandPalette.svelte";
	import { ColumnResizeStore } from "../lib/columnResize.svelte";
	import { routerContext, themeContext } from "../lib/context";
	import { DashboardsStore } from "../lib/dashboards.svelte";
	import { DismissStore } from "../lib/dismiss.svelte";
	import { FilterSortStore } from "../lib/filterSort.svelte";
	import { GroupCollapseStore } from "../lib/groupCollapse.svelte";
	import { IgnoreRuleStore } from "../lib/ignoreRule.svelte";
	import { KeyboardStore } from "../lib/keyboard.svelte";
	import { MarkReadStore } from "../lib/markRead.svelte";
	import { SearchStore } from "../lib/search.svelte";
	import { SnapshotStore } from "../lib/snapshot.svelte";
	import type { DashboardGroup, DashboardItem } from "../types";
	import { notificationKey } from "../types";
	import CenteredNotice from "./CenteredNotice.svelte";
	import CommandPalette from "./CommandPalette.svelte";
	import EmptyState from "./EmptyState.svelte";
	import ErrorToast from "./ErrorToast.svelte";
	import FilterBar from "./FilterBar.svelte";
	import IgnoreRuleDialog from "./IgnoreRuleDialog.svelte";
	import LoadingSkeleton from "./LoadingSkeleton.svelte";
	import NotificationTable from "./NotificationTable.svelte";
	import PollerWarning from "./PollerWarning.svelte";
	import RowContextMenu from "./RowContextMenu.svelte";
	import ShortcutsModal from "./ShortcutsModal.svelte";
	import Toolbar from "./Toolbar.svelte";
	import UndoToast from "./UndoToast.svelte";

	// The active dashboard name is read reactively from the router by the
	// DashboardsStore; nothing else in the shell needs the route prop.
	const router = routerContext.get();
	const theme = themeContext.get();

	let toastError = $state<string | null>(null);
	let showShortcuts = $state(false);

	function setToastError(message: string | null) {
		toastError = message;
	}

	const snap = new SnapshotStore();
	const dashboards = new DashboardsStore(router, snap);
	const filterSort = new FilterSortStore(router, () => snap.snapshot);
	const search = new SearchStore(router);
	const groupCollapse = new GroupCollapseStore();

	const allItems = $derived<DashboardItem[]>(
		snap.snapshot ? snap.snapshot.groups.flatMap((g) => g.items) : [],
	);
	const currentThreadIds = $derived(
		new Set(allItems.map((item) => notificationKey(item))),
	);

	const dismiss = new DismissStore(
		() => snap.refresh(),
		setToastError,
		() => currentThreadIds,
	);
	const markRead = new MarkReadStore(() => snap.refresh(), setToastError);
	const ignoreRule = new IgnoreRuleStore(() => dashboards.currentDashboard);
	const columnResize = new ColumnResizeStore();
	const notifications = new BrowserNotificationsStore(
		() => allItems,
		() => snap.snapshot?.notifications_config?.browser_tab ?? null,
	);
	const commandPalette = new CommandPaletteStore();

	function handleDismissFocused() {
		const focused = document.activeElement;
		const row = focused?.closest<HTMLTableRowElement>("tr[data-thread-id]");
		const accountId = row?.dataset.accountId;
		const threadId = row?.dataset.threadId;
		if (accountId && threadId) dismiss.dismiss(accountId, threadId);
	}

	function handleDismissGroupRead(_groupName: string, items: DashboardItem[]) {
		for (const item of items) {
			if (!item.unread) dismiss.dismiss(item.account_id, item.thread_id);
		}
	}

	function focusSelector(selector: string) {
		document.querySelector<HTMLElement>(selector)?.focus();
	}

	const keyboard = new KeyboardStore({
		onRefresh: () => void snap.refresh(),
		onFocusFilters: () => focusSelector("[data-filter-focus]"),
		onDismissFocused: handleDismissFocused,
		onToggleShortcuts: () => (showShortcuts = !showShortcuts),
		onCommandPalette: () => commandPalette.toggle(),
		onFocusSearch: () => focusSelector("[data-search-input]"),
	});

	// Wire reactive effects (all during component init).
	dashboards.bind();
	columnResize.bind();
	dismiss.bind();
	ignoreRule.bind();
	notifications.bind();
	keyboard.bind();
	$effect(() => {
		groupCollapse.setDashboard(dashboards.currentDashboard);
	});

	const filters = $derived(filterSort.filterState);
	const effectiveUnreadFilter = $derived(filterSort.effectiveUnreadFilter);

	const hasFilters = $derived(
		effectiveUnreadFilter !== "all" ||
			filters.reason.length > 0 ||
			filters.repository !== "" ||
			search.query.trim() !== "",
	);

	const filteredGroups = $derived.by<DashboardGroup[]>(() => {
		const snapshot = snap.snapshot;
		if (!snapshot) return [];
		const hidden = dismiss.hiddenThreadIds;
		return snapshot.groups
			.map((group) => ({
				...group,
				items: group.items.filter((item) => {
					if (hidden.has(notificationKey(item))) return false;
					if (effectiveUnreadFilter !== "all") {
						if (effectiveUnreadFilter === "unread" && !item.unread) return false;
						if (effectiveUnreadFilter === "read" && item.unread) return false;
					}
					if (filters.reason.length > 0 && !filters.reason.includes(item.reason))
						return false;
					if (filters.repository && item.repository !== filters.repository)
						return false;
					if (!search.matches(item)) return false;
					return true;
				}),
			}))
			.filter((group) => group.items.length > 0);
	});

	function clearAllFilters() {
		filterSort.clearFilters();
		search.clear();
	}

	function handleUnreadFilterChange<K extends "unread" | "reason" | "repository">(
		key: K,
		value: string | string[],
	) {
		if (key === "unread" && !filterSort.dashboardAllowsRead && value !== "unread") {
			filterSort.setFilter("unread", "unread");
			return;
		}
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		filterSort.setFilter(key, value as never);
	}

	const notifConfig = $derived(snap.snapshot?.notifications_config?.browser_tab ?? null);

	const commands = $derived.by<Command[]>(() => {
		const list: Command[] = [];
		for (const dashName of dashboards.dashboardNames) {
			if (dashName === dashboards.currentDashboard) continue;
			list.push({
				id: `dashboard:${dashName}`,
				label: `Switch to dashboard: ${dashName}`,
				run: () => dashboards.setDashboard(dashName),
			});
		}
		list.push(
			{ id: "refresh", label: "Refresh notifications", hint: "R", run: () => void snap.refresh() },
			{ id: "theme", label: "Toggle light / dark theme", run: () => theme.toggle() },
			{ id: "theme-system", label: "Use system theme", run: () => theme.setPreference("system") },
			{ id: "clear", label: "Clear all filters", run: clearAllFilters },
			{
				id: "unread",
				label: "Cycle unread filter",
				run: () => {
					const order = ["all", "unread", "read"] as const;
					const next = order[(order.indexOf(filters.unread) + 1) % order.length];
					handleUnreadFilterChange("unread", next);
				},
			},
			{ id: "reset-layout", label: "Reset column layout", run: columnResize.resetLayout },
			{ id: "shortcuts", label: "Show keyboard shortcuts", hint: "?", run: () => (showShortcuts = true) },
		);
		if (notifications.supported && notifConfig?.enabled) {
			list.push(
				notifications.active
					? { id: "notif", label: "Disable browser notifications", run: notifications.disable }
					: { id: "notif", label: "Enable browser notifications", run: () => void notifications.enable() },
			);
		}
		return list;
	});

	const filteredCommands = $derived(commandPalette.filter(commands));

	function runCommand(command: Command) {
		command.run();
		commandPalette.close();
	}
</script>

<div class="app-shell" data-testid="app-shell">
	{#if snap.refreshing}
		<div class="refresh-bar" aria-hidden="true"></div>
	{/if}

	<Toolbar
		dashboardNames={dashboards.dashboardNames}
		currentDashboard={dashboards.currentDashboard}
		onDashboardChange={(dashName) => dashboards.setDashboard(dashName)}
		onRefresh={() => void snap.refresh()}
		refreshing={snap.manualRefreshing}
		summary={snap.snapshot?.summary ?? null}
		shortcutsOpen={showShortcuts}
		onToggleShortcuts={() => (showShortcuts = !showShortcuts)}
		notifSupported={notifications.supported}
		notifActive={notifications.active}
		notifPermission={notifications.permission}
		onEnableNotifications={() => void notifications.enable()}
		onDisableNotifications={notifications.disable}
		onResetLayout={columnResize.resetLayout}
		searchQuery={search.query}
		onSearchChange={search.setQuery}
		onOpenCommandPalette={commandPalette.openPalette}
	/>

	<ShortcutsModal open={showShortcuts} onClose={() => (showShortcuts = false)} />

	{#if snap.snapshot}
		<FilterBar
			filters={{ ...filters, unread: effectiveUnreadFilter }}
			includeRead={filterSort.dashboardAllowsRead}
			items={allItems}
			onFilterChange={handleUnreadFilterChange}
			onClearFilters={clearAllFilters}
			generatedAt={snap.snapshot.generated_at}
		/>
	{/if}

	{#if snap.snapshot?.poller}
		<PollerWarning poller={snap.snapshot.poller} />
	{/if}

	<main class="board">
		{#if snap.loading}
			<LoadingSkeleton />
		{:else if snap.error}
			<EmptyState
				hasFilters={false}
				totalItems={0}
				onClearFilters={clearAllFilters}
				onRetry={() => void snap.refresh()}
				error={snap.error}
			/>
		{:else if filteredGroups.length === 0}
			<EmptyState
				hasFilters={hasFilters}
				totalItems={snap.snapshot?.total_items ?? 0}
				onClearFilters={clearAllFilters}
				onRetry={() => void snap.refresh()}
				filterContext={{
					unread: effectiveUnreadFilter,
					reason: filters.reason,
					repository: filters.repository,
				}}
			/>
		{:else}
			<svelte:boundary>
				<NotificationTable
					groups={filteredGroups}
					sortColumn={filterSort.sortColumn}
					sortDirection={filterSort.sortDirection}
					onSort={filterSort.handleSort}
					onDismiss={dismiss.dismiss}
					onDismissGroupRead={handleDismissGroupRead}
					onMarkGroupRead={markRead.markGroupRead}
					markingGroupNames={markRead.markingGroupNames}
					onOpenTarget={markRead.openTarget}
					onRequestIgnoreRule={ignoreRule.requestRule}
					pendingDismissals={new Set(dismiss.pending.keys())}
					columnWidths={columnResize.widths}
					onResizeStart={columnResize.startResize}
					onResetColumnWidth={columnResize.resetColumnWidth}
					isCollapsed={(groupName) => groupCollapse.isCollapsed(groupName)}
					onToggleCollapse={groupCollapse.toggle}
				/>
				{#snippet failed(error, reset)}
					<CenteredNotice
						variant="error"
						title="Something went wrong"
						body={error instanceof Error ? error.message : String(error)}
					>
						<button
							type="button"
							onclick={() => {
								reset();
								void snap.refresh();
							}}
						>
							Try again
						</button>
					</CenteredNotice>
				{/snippet}
			</svelte:boundary>
		{/if}
	</main>

	{#if ignoreRule.menu}
		{@const menu = ignoreRule.menu}
		<RowContextMenu x={menu.x} y={menu.y} onCreateRule={() => ignoreRule.openDialog(menu.item)} />
	{/if}

	{#if ignoreRule.dialogItem}
		<IgnoreRuleDialog
			item={ignoreRule.dialogItem}
			dashboardName={dashboards.currentDashboard}
			snippets={ignoreRule.snippets}
			loading={ignoreRule.loading}
			error={ignoreRule.error}
			onClose={ignoreRule.closeDialog}
		/>
	{/if}

	{#if toastError}
		<ErrorToast message={toastError} onDismiss={() => setToastError(null)} />
	{/if}

	<UndoToast count={dismiss.count} onUndoAll={dismiss.undoAll} />

	{#if commandPalette.open}
		<CommandPalette
			query={commandPalette.query}
			commands={filteredCommands}
			onQueryChange={(value) => (commandPalette.query = value)}
			onRun={runCommand}
			onClose={commandPalette.close}
		/>
	{/if}
</div>

<style>
	.app-shell {
		display: flex;
		flex-direction: column;
		min-height: 100dvh;
		max-width: 1234px;
		margin-inline: auto;
	}
	.board {
		flex: 1;
		overflow-x: auto;
	}
	.refresh-bar {
		position: fixed;
		top: 0;
		left: 0;
		width: 100%;
		height: 2px;
		background: var(--accent);
		animation: refresh-slide 1.5s ease-in-out infinite;
		z-index: 1000;
	}
	@keyframes refresh-slide {
		0% {
			transform: translateX(-100%);
		}
		100% {
			transform: translateX(100%);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.refresh-bar {
			animation: none;
		}
	}
</style>

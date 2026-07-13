<script lang="ts">
	import { Bell, BellOff, Command, Keyboard, RotateCcw, RefreshCw } from "@lucide/svelte";
	import type { NotifPermission } from "../lib/browserNotifications.svelte";
	import type { DashboardSummary } from "../types";
	import SearchInput from "./SearchInput.svelte";
	import ThemeToggle from "./ThemeToggle.svelte";

	interface Props {
		dashboardNames: string[];
		currentDashboard: string | null;
		onDashboardChange: (name: string) => void;
		onRefresh: () => void;
		refreshing: boolean;
		summary: DashboardSummary | null;
		shortcutsOpen: boolean;
		onToggleShortcuts: () => void;
		notifSupported: boolean;
		notifActive: boolean;
		notifPermission: NotifPermission;
		onEnableNotifications: () => void;
		onDisableNotifications: () => void;
		onResetLayout: () => void;
		searchQuery: string;
		onSearchChange: (value: string) => void;
		onOpenCommandPalette: () => void;
	}

	let {
		dashboardNames,
		currentDashboard,
		onDashboardChange,
		onRefresh,
		refreshing,
		summary,
		shortcutsOpen,
		onToggleShortcuts,
		notifSupported,
		notifActive,
		notifPermission,
		onEnableNotifications,
		onDisableNotifications,
		onResetLayout,
		searchQuery,
		onSearchChange,
		onOpenCommandPalette,
	}: Props = $props();
</script>

<div class="toolbar">
	<span class="brand">
		<img class="brand-icon" src="/assets/favicon.svg" alt="" aria-hidden="true" />
		<span class="app-name" data-testid="app-name">Corvix</span>
	</span>
	{#if summary}
		<span class="stats">
			{summary.unread_items + summary.read_items} notifications ·
			{summary.unread_items} unread · {summary.repository_count} repos
		</span>
	{/if}
	<div class="toolbar-right">
		<SearchInput value={searchQuery} onChange={onSearchChange} />
		<button
			type="button"
			class="icon-btn"
			onclick={onOpenCommandPalette}
			title="Command palette (Cmd/Ctrl+K)"
			aria-label="Open command palette"
		>
			<Command size={16} aria-hidden="true" />
		</button>
		<ThemeToggle />
		<button
			type="button"
			class="icon-btn"
			onclick={onToggleShortcuts}
			aria-expanded={shortcutsOpen}
			aria-controls="shortcuts-panel"
			title="Keyboard shortcuts (?)"
			aria-label="Keyboard shortcuts"
		>
			<Keyboard size={16} aria-hidden="true" />
		</button>
		<button
			type="button"
			class="icon-btn"
			onclick={onResetLayout}
			title="Reset table column widths to their defaults"
			aria-label="Reset column layout"
		>
			<RotateCcw size={16} aria-hidden="true" />
		</button>
		{#if notifSupported}
			{#if notifPermission === "denied"}
				<span class="notif-denied" title="Notifications blocked by browser">
					<BellOff size={16} aria-hidden="true" /> Blocked
				</span>
			{:else if notifActive}
				<button
					type="button"
					class="icon-btn notif-on"
					onclick={onDisableNotifications}
					title="Browser notifications enabled — click to disable"
					aria-label="Disable browser notifications"
				>
					<Bell size={16} aria-hidden="true" />
				</button>
			{:else}
				<button
					type="button"
					class="icon-btn"
					onclick={onEnableNotifications}
					title={notifPermission === "default"
						? "Click to enable browser notifications"
						: "Enable browser notifications"}
					aria-label="Enable browser notifications"
				>
					<BellOff size={16} aria-hidden="true" />
				</button>
			{/if}
		{/if}
		{#if dashboardNames.length > 1}
			<select
				class="dashboard-select"
				value={currentDashboard ?? ""}
				onchange={(event) =>
					onDashboardChange((event.currentTarget as HTMLSelectElement).value)}
				aria-label="Select dashboard"
			>
				{#each dashboardNames as name (name)}
					<option value={name}>{name}</option>
				{/each}
			</select>
		{/if}
		<button
			type="button"
			class="refresh-btn"
			class:refreshing
			onclick={onRefresh}
			aria-label="Refresh"
			disabled={refreshing}
		>
			<RefreshCw size={15} aria-hidden="true" />
			{refreshing ? "Refreshing" : "Refresh"}
		</button>
	</div>
</div>

<style>
	.toolbar {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 10px 16px;
		border-bottom: 1px solid var(--line);
		flex-wrap: wrap;
	}
	.brand {
		display: inline-flex;
		align-items: center;
		gap: 8px;
	}
	.brand-icon {
		width: 20px;
		height: 20px;
	}
	.app-name {
		font-weight: 700;
		font-size: var(--text-lg);
		color: var(--ink);
		letter-spacing: -0.01em;
	}
	.stats {
		font-size: var(--text-sm);
		color: var(--muted);
	}
	.toolbar-right {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-left: auto;
		flex-wrap: wrap;
	}
	.icon-btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 30px;
		height: 28px;
		padding: 0;
		background: var(--surface-raised);
		color: var(--ink-secondary);
		border: 1px solid var(--line);
		border-radius: var(--radius-sm);
	}
	.icon-btn:hover:not(:disabled) {
		border-color: var(--accent);
		color: var(--accent);
	}
	.notif-on {
		color: var(--accent);
		border-color: var(--accent);
	}
	.notif-denied {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		font-size: var(--text-xs);
		color: var(--muted);
	}
	.dashboard-select {
		background: var(--surface-raised);
		color: var(--ink);
		border: 1px solid var(--line);
		border-radius: var(--radius-sm);
		padding: 4px 8px;
		font-size: var(--text-sm);
	}
	.refresh-btn {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		background: var(--surface-raised);
		color: var(--ink-secondary);
		border: 1px solid var(--line);
		border-radius: var(--radius-sm);
		padding: 4px 10px;
		font-size: var(--text-sm);
	}
	.refresh-btn:hover:not(:disabled) {
		border-color: var(--accent);
		color: var(--accent);
	}
	.refresh-btn:disabled {
		opacity: 0.7;
		cursor: default;
	}
	.refresh-btn.refreshing :global(svg) {
		animation: spin 1s linear infinite;
	}
	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
</style>

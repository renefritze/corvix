<script lang="ts">
	import { ChevronDown, X } from "@lucide/svelte";
	import type { DashboardItem, FilterState } from "../types";

	interface Props {
		filters: FilterState;
		includeRead: boolean;
		items: DashboardItem[];
		onFilterChange: <K extends keyof FilterState>(
			key: K,
			value: FilterState[K],
		) => void;
		onClearFilters: () => void;
		generatedAt: string | null;
	}

	let { filters, includeRead, items, onFilterChange, onClearFilters, generatedAt }: Props =
		$props();

	const reasonListId = "reason-filter-options";
	let reasonMenuOpen = $state(false);
	let reasonPicker = $state<HTMLDivElement | null>(null);

	const reasons = $derived(
		Array.from(new Set(items.map((i) => i.reason))).sort((a, b) =>
			a.localeCompare(b),
		),
	);
	const missingReasons = $derived(
		Array.from(new Set(filters.reason.filter((r) => !reasons.includes(r)))),
	);
	const repositories = $derived(
		Array.from(new Set(items.map((i) => i.repository))).sort((a, b) =>
			a.localeCompare(b),
		),
	);
	const selectedRepositoryMissing = $derived(
		filters.repository !== "" && !repositories.includes(filters.repository),
	);
	const missingFilterLabel = $derived(
		filters.unread === "unread" ? "no unread notifications" : "no matching notifications",
	);
	const selectedReasonSet = $derived(new Set(filters.reason));
	const reasonOptions = $derived([
		...missingReasons.map((reason) => ({
			reason,
			label: `${reason} (${missingFilterLabel})`,
			missing: true,
		})),
		...reasons.map((reason) => ({ reason, label: reason, missing: false })),
	]);

	$effect(() => {
		if (!reasonMenuOpen) return;
		const handleClickAway = (event: MouseEvent) => {
			if (!(event.target instanceof Node)) return;
			if (reasonPicker?.contains(event.target)) return;
			reasonMenuOpen = false;
		};
		const handleEscape = (event: KeyboardEvent) => {
			if (event.key === "Escape") reasonMenuOpen = false;
		};
		document.addEventListener("mousedown", handleClickAway);
		document.addEventListener("keydown", handleEscape);
		return () => {
			document.removeEventListener("mousedown", handleClickAway);
			document.removeEventListener("keydown", handleEscape);
		};
	});

	function toggleReason(reason: string) {
		if (selectedReasonSet.has(reason)) {
			onFilterChange("reason", filters.reason.filter((v) => v !== reason));
			return;
		}
		onFilterChange("reason", [...filters.reason, reason]);
	}

	function removeReason(reason: string) {
		onFilterChange("reason", filters.reason.filter((v) => v !== reason));
	}
</script>

<div class="filter-row">
	<select
		class="filter-select"
		data-filter-focus
		value={filters.unread}
		onchange={(event) =>
			onFilterChange(
				"unread",
				(event.currentTarget as HTMLSelectElement).value as FilterState["unread"],
			)}
		aria-label="Unread state filter"
	>
		<option value="all" disabled={!includeRead}>
			{includeRead ? "All" : "🔒 All (disabled by dashboard)"}
		</option>
		<option value="unread">Unread only</option>
		<option value="read" disabled={!includeRead}>
			{includeRead ? "Read only" : "🔒 Read only (disabled by dashboard)"}
		</option>
	</select>

	<div class="reason-picker" bind:this={reasonPicker}>
		<button
			type="button"
			class="reason-trigger"
			class:open={reasonMenuOpen}
			aria-label="Reason filter"
			aria-expanded={reasonMenuOpen}
			aria-controls={reasonListId}
			onclick={() => (reasonMenuOpen = !reasonMenuOpen)}
		>
			{#if filters.reason.length === 0}
				<span class="reason-placeholder">All reasons</span>
			{:else if filters.reason.length <= 2}
				<span class="reason-summary">{filters.reason.join(", ")}</span>
			{:else}
				<span class="reason-summary">{filters.reason.length} reasons</span>
			{/if}
			<ChevronDown size={13} aria-hidden="true" />
		</button>
		{#if filters.reason.length > 0}
			<span class="reason-chips" aria-label="Selected reasons">
				{#each filters.reason as reason (reason)}
					<span class="reason-chip">
						<span class="reason-chip-text">{reason}</span>
						<button
							type="button"
							class="reason-chip-remove"
							aria-label={`Remove ${reason} reason filter`}
							onclick={() => removeReason(reason)}
						>
							<X size={11} aria-hidden="true" />
						</button>
					</span>
				{/each}
			</span>
		{/if}
		{#if reasonMenuOpen}
			<ul id={reasonListId} class="reason-menu" aria-label="Reason options">
				{#each reasonOptions as option (option.reason)}
					<li>
						<button
							type="button"
							class="reason-option"
							class:selected={selectedReasonSet.has(option.reason)}
							class:missing={option.missing}
							onclick={() => toggleReason(option.reason)}
						>
							<span class="reason-check" aria-hidden="true">
								{selectedReasonSet.has(option.reason) ? "✓" : ""}
							</span>
							<span class="reason-option-label">{option.label}</span>
						</button>
					</li>
				{/each}
			</ul>
		{/if}
	</div>

	<select
		class="filter-select"
		value={filters.repository}
		onchange={(event) =>
			onFilterChange("repository", (event.currentTarget as HTMLSelectElement).value)}
		aria-label="Repository filter"
	>
		<option value="">All repositories</option>
		{#if selectedRepositoryMissing}
			<option value={filters.repository}>
				{`${filters.repository} (${missingFilterLabel})`}
			</option>
		{/if}
		{#each repositories as repository (repository)}
			<option value={repository}>{repository}</option>
		{/each}
	</select>

	<button type="button" class="filter-clear" onclick={onClearFilters}>Clear</button>

	{#if generatedAt}
		<span class="snapshot-time">
			Snapshot: {new Date(generatedAt).toLocaleTimeString()}
		</span>
	{/if}
</div>

<style>
	.filter-row {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 8px 16px;
		border-bottom: 1px solid var(--line);
		flex-wrap: wrap;
	}
	.filter-select,
	.filter-clear {
		background: var(--surface-raised);
		color: var(--ink);
		border: 1px solid var(--line);
		border-radius: var(--radius-sm);
		padding: 4px 8px;
		font-size: var(--text-sm);
	}
	.filter-clear:hover {
		border-color: var(--accent);
		color: var(--accent);
	}
	.reason-picker {
		position: relative;
		display: inline-flex;
		align-items: center;
		gap: 6px;
		flex-wrap: wrap;
	}
	.reason-trigger {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		background: var(--surface-raised);
		color: var(--ink);
		border: 1px solid var(--line);
		border-radius: var(--radius-sm);
		padding: 4px 8px;
		font-size: var(--text-sm);
	}
	.reason-trigger.open,
	.reason-trigger:hover {
		border-color: var(--accent);
	}
	.reason-placeholder {
		color: var(--muted);
	}
	.reason-chips {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		flex-wrap: wrap;
	}
	.reason-chip {
		display: inline-flex;
		align-items: center;
		gap: 2px;
		background: color-mix(in srgb, var(--accent) 12%, transparent);
		color: var(--accent);
		border-radius: 999px;
		padding: 1px 4px 1px 8px;
		font-size: var(--text-xs);
	}
	.reason-chip-remove {
		display: inline-flex;
		align-items: center;
		background: none;
		border: none;
		color: inherit;
		padding: 1px;
		border-radius: 999px;
	}
	.reason-chip-remove:hover {
		background: color-mix(in srgb, var(--accent) 25%, transparent);
	}
	.reason-menu {
		position: absolute;
		top: calc(100% + 4px);
		left: 0;
		z-index: 50;
		list-style: none;
		margin: 0;
		padding: 4px;
		min-width: 200px;
		max-height: 280px;
		overflow-y: auto;
		background: var(--surface-raised);
		border: 1px solid var(--line-strong);
		border-radius: var(--radius-md);
		box-shadow: var(--shadow-md);
	}
	.reason-option {
		display: flex;
		align-items: center;
		gap: 8px;
		width: 100%;
		text-align: left;
		background: none;
		border: none;
		border-radius: var(--radius-sm);
		padding: 5px 8px;
		font-size: var(--text-sm);
		color: var(--ink);
	}
	.reason-option:hover {
		background: var(--row-hover);
	}
	.reason-option.selected {
		color: var(--accent);
	}
	.reason-option.missing .reason-option-label {
		color: var(--muted);
		font-style: italic;
	}
	.reason-check {
		width: 12px;
		color: var(--accent);
	}
	.snapshot-time {
		margin-left: auto;
		font-size: var(--text-xs);
		color: var(--muted);
	}
</style>

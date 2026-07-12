<script lang="ts">
	import { X } from "@lucide/svelte";
	import type { DashboardItem, RuleSnippetsPayload } from "../types";

	interface Props {
		item: DashboardItem;
		dashboardName: string | null;
		snippets: RuleSnippetsPayload | null;
		loading: boolean;
		error: string | null;
		onClose: () => void;
	}

	let { item, dashboardName, snippets, loading, error, onClose }: Props = $props();

	let copyStatus = $state<string | null>(null);

	const dashboardContextSnippet = $derived(
		snippets?.dashboard_ignore_rule_with_context_snippet ?? null,
	);
	const globalContextSnippet = $derived(
		snippets?.global_exclude_rule_with_context_snippet ?? null,
	);

	async function copyText(value: string, label: string) {
		try {
			await navigator.clipboard.writeText(value);
			copyStatus = `${label} copied`;
		} catch {
			copyStatus = `Failed to copy ${label.toLowerCase()}`;
		}
	}
</script>

<dialog
	class="ignore-dialog"
	aria-label="Ignore rule snippets"
	open
	oncancel={(event) => {
		event.preventDefault();
		onClose();
	}}
	onclose={onClose}
>
	<div class="ignore-header">
		<h2>Create ignore rule</h2>
		<button type="button" aria-label="Close ignore rule dialog" onclick={onClose}>
			<X size={16} aria-hidden="true" />
		</button>
	</div>
	<p class="ignore-subtitle">Notification: {item.subject_title}</p>

	{#if loading}
		<p class="ignore-status">Loading snippets...</p>
	{/if}
	{#if error}
		<p class="ignore-status error">{error}</p>
	{/if}
	{#if copyStatus && !error}
		<p class="ignore-status">{copyStatus}</p>
	{/if}

	{#if snippets && !loading && !error}
		<div class="ignore-content">
			<section class="snippet-card">
				<h3>Dashboard ignore rule</h3>
				<p>
					Paste under
					<code>{`dashboards: - name: ${dashboardName ?? snippets.dashboard_name} -> ignore_rules:`}</code>
				</p>
				<textarea
					readonly
					rows={dashboardContextSnippet ? 8 : 6}
					value={snippets.dashboard_ignore_rule_snippet}
				></textarea>
				<div class="snippet-actions">
					<button
						type="button"
						onclick={() =>
							void copyText(snippets.dashboard_ignore_rule_snippet, "Dashboard snippet")}
					>
						Copy
					</button>
					{#if dashboardContextSnippet}
						<button
							type="button"
							onclick={() =>
								void copyText(dashboardContextSnippet, "Dashboard context snippet")}
						>
							Copy context-aware variant
						</button>
					{/if}
				</div>
			</section>
			<section class="snippet-card">
				<h3>Global exclude rule</h3>
				<p>Paste under <code>rules.global</code></p>
				<textarea
					readonly
					rows={globalContextSnippet ? 9 : 7}
					value={snippets.global_exclude_rule_snippet}
				></textarea>
				<div class="snippet-actions">
					<button
						type="button"
						onclick={() =>
							void copyText(snippets.global_exclude_rule_snippet, "Global snippet")}
					>
						Copy
					</button>
					{#if globalContextSnippet}
						<button
							type="button"
							onclick={() =>
								void copyText(globalContextSnippet, "Global context snippet")}
						>
							Copy context-aware variant
						</button>
					{/if}
				</div>
			</section>
		</div>
	{/if}
</dialog>

<style>
	.ignore-dialog {
		position: fixed;
		inset: 0;
		margin: auto;
		width: min(640px, calc(100vw - 32px));
		max-height: calc(100vh - 64px);
		overflow-y: auto;
		background: var(--surface-raised);
		color: var(--ink);
		border: 1px solid var(--line-strong);
		border-radius: var(--radius-lg);
		box-shadow: var(--shadow-lg);
		padding: 20px;
		z-index: 300;
	}
	.ignore-dialog::backdrop {
		background: var(--overlay);
	}
	.ignore-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 4px;
	}
	.ignore-header h2 {
		font-size: var(--text-lg);
		font-weight: 600;
	}
	.ignore-header button {
		display: inline-flex;
		background: none;
		border: none;
		color: var(--muted);
		padding: 4px;
		border-radius: var(--radius-sm);
	}
	.ignore-header button:hover {
		color: var(--ink);
	}
	.ignore-subtitle {
		font-size: var(--text-sm);
		color: var(--muted);
		margin-bottom: 12px;
	}
	.ignore-status {
		font-size: var(--text-sm);
		color: var(--ink-secondary);
		margin-bottom: 8px;
	}
	.ignore-status.error {
		color: var(--danger);
	}
	.ignore-content {
		display: flex;
		flex-direction: column;
		gap: 16px;
	}
	.snippet-card h3 {
		font-size: var(--text-md);
		font-weight: 600;
		margin-bottom: 4px;
	}
	.snippet-card p {
		font-size: var(--text-sm);
		color: var(--muted);
		margin-bottom: 6px;
	}
	.snippet-card code {
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		background: var(--bg-subtle);
		padding: 1px 4px;
		border-radius: 3px;
	}
	.snippet-card textarea {
		width: 100%;
		font-family: var(--font-mono);
		font-size: var(--text-xs);
		background: var(--bg-subtle);
		color: var(--ink);
		border: 1px solid var(--line);
		border-radius: var(--radius-sm);
		padding: 8px;
		resize: vertical;
	}
	.snippet-actions {
		display: flex;
		gap: 8px;
		margin-top: 6px;
		flex-wrap: wrap;
	}
	.snippet-actions button {
		background: var(--surface);
		color: var(--ink-secondary);
		border: 1px solid var(--line);
		border-radius: var(--radius-sm);
		padding: 4px 10px;
		font-size: var(--text-sm);
	}
	.snippet-actions button:hover {
		border-color: var(--accent);
		color: var(--accent);
	}
</style>

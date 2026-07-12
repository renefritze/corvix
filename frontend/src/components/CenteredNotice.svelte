<script lang="ts">
	import type { Snippet } from "svelte";

	interface Props {
		title: string;
		body: string;
		variant?: "neutral" | "error";
		testid?: string;
		role?: "alert" | "status" | undefined;
		children?: Snippet;
	}

	let {
		title,
		body,
		variant = "neutral",
		testid = "empty-state",
		role = undefined,
		children,
	}: Props = $props();
</script>

<div class="notice" class:error={variant === "error"} data-testid={testid} {role}>
	<p class="title" data-testid="empty-title">{title}</p>
	<p class="body" data-testid="empty-body">{body}</p>
	{#if children}
		<div class="actions">{@render children()}</div>
	{/if}
</div>

<style>
	.notice {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 6px;
		text-align: center;
		padding: 56px 24px;
		margin: 24px auto;
		max-width: 420px;
	}
	.title {
		font-size: var(--text-lg);
		font-weight: 600;
		color: var(--ink);
	}
	.error .title {
		color: var(--danger);
	}
	.body {
		font-size: var(--text-sm);
		color: var(--muted);
		line-height: 1.5;
	}
	.actions {
		margin-top: 10px;
		display: flex;
		gap: 8px;
	}
	.actions :global(button) {
		background: var(--surface-raised);
		color: var(--ink);
		border: 1px solid var(--line);
		border-radius: var(--radius-sm);
		padding: 6px 12px;
		font-size: var(--text-sm);
	}
	.actions :global(button:hover) {
		border-color: var(--accent);
		color: var(--accent);
	}
</style>

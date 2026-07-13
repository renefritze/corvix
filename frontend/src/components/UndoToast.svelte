<script lang="ts">
	import { fly } from "svelte/transition";
	import { prefersReducedMotion } from "../lib/motion.svelte";

	interface Props {
		count: number;
		onUndoAll: () => void;
	}

	let { count, onUndoAll }: Props = $props();
	const flyParams = $derived(prefersReducedMotion() ? { duration: 0 } : { y: 12, duration: 180 });
</script>

{#if count > 0}
	<div
		class="undo-toast"
		data-testid="undo-toast"
		role="status"
		aria-live="polite"
		transition:fly={flyParams}
	>
		<span>
			{count} notification{count > 1 ? "s" : ""} dismissing…
		</span>
		<button type="button" onclick={onUndoAll}>Undo</button>
	</div>
{/if}

<style>
	.undo-toast {
		position: fixed;
		bottom: 24px;
		left: 50%;
		transform: translateX(-50%);
		display: flex;
		align-items: center;
		gap: 14px;
		background: var(--surface-raised);
		border: 1px solid var(--line-strong);
		border-radius: var(--radius-md);
		box-shadow: var(--shadow-lg);
		padding: 10px 16px;
		font-size: var(--text-sm);
		color: var(--ink);
		z-index: 120;
	}
	.undo-toast button {
		background: transparent;
		border: 1px solid var(--line);
		border-radius: var(--radius-sm);
		color: var(--accent);
		padding: 3px 10px;
		font-size: var(--text-sm);
		font-weight: 600;
	}
	.undo-toast button:hover {
		border-color: var(--accent);
	}
</style>

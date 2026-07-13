<script lang="ts">
	import { X } from "@lucide/svelte";
	import { fly } from "svelte/transition";
	import { prefersReducedMotion } from "../lib/motion.svelte";

	interface Props {
		message: string;
		onDismiss: () => void;
	}

	let { message, onDismiss }: Props = $props();
	const flyParams = $derived(prefersReducedMotion() ? { duration: 0 } : { y: 12, duration: 180 });
</script>

<div class="error-toast" role="alert" transition:fly={flyParams}>
	<span>{message}</span>
	<button type="button" aria-label="Dismiss error" onclick={onDismiss}>
		<X size={14} aria-hidden="true" />
	</button>
</div>

<style>
	.error-toast {
		position: fixed;
		bottom: 24px;
		left: 24px;
		display: flex;
		align-items: center;
		gap: 12px;
		background: var(--surface-raised);
		border: 1px solid var(--danger);
		border-radius: var(--radius-md);
		padding: 10px 14px;
		font-size: var(--text-sm);
		color: var(--danger);
		box-shadow: var(--shadow-lg);
		z-index: 130;
	}
	.error-toast button {
		display: inline-flex;
		background: none;
		border: none;
		color: var(--danger);
		padding: 2px;
	}
</style>

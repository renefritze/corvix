<script lang="ts">
	import { Bird } from "@lucide/svelte";
</script>

<div class="app-shell" data-testid="app-shell">
	<header class="brand">
		<Bird size={18} aria-hidden="true" />
		<span data-testid="app-name">Corvix</span>
	</header>
</div>

<style>
	.app-shell {
		min-height: 100dvh;
		max-width: 1234px;
		margin-inline: auto;
	}
	.brand {
		display: inline-flex;
		align-items: center;
		gap: 8px;
		padding: 12px 16px;
		color: var(--ink);
		font-weight: 600;
	}
</style>

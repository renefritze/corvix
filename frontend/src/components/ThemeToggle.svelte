<script lang="ts">
	import { Moon, Sun } from "@lucide/svelte";
	import { themeContext } from "../lib/context";

	const theme = themeContext.get();
</script>

<button
	type="button"
	class="theme-toggle"
	onclick={() => theme.toggle()}
	title="Toggle light / dark theme"
	aria-label={`Switch to ${theme.resolved === "dark" ? "light" : "dark"} theme`}
>
	{#if theme.resolved === "dark"}
		<Sun size={16} aria-hidden="true" />
	{:else}
		<Moon size={16} aria-hidden="true" />
	{/if}
</button>

<style>
	.theme-toggle {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		background: var(--surface-raised);
		color: var(--ink-secondary);
		border: 1px solid var(--line);
		border-radius: var(--radius-sm);
		width: 30px;
		height: 28px;
		padding: 0;
	}
	.theme-toggle:hover {
		border-color: var(--accent);
		color: var(--accent);
	}
</style>

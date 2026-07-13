<script lang="ts">
	import { Search } from "@lucide/svelte";

	interface Props {
		value: string;
		onChange: (value: string) => void;
	}

	let { value, onChange }: Props = $props();
</script>

<label class="search">
	<Search size={14} class="search-icon" aria-hidden="true" />
	<input
		type="search"
		data-search-input
		aria-label="Search notifications"
		placeholder="Search…"
		{value}
		oninput={(event) => onChange((event.currentTarget as HTMLInputElement).value)}
	/>
</label>

<style>
	.search {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		background: var(--surface-raised);
		border: 1px solid var(--line);
		border-radius: var(--radius-sm);
		padding: 0 8px;
		height: 28px;
		color: var(--muted);
	}
	.search:focus-within {
		border-color: var(--accent);
	}
	.search input {
		background: transparent;
		border: none;
		outline: none;
		color: var(--ink);
		font: inherit;
		font-size: var(--text-sm);
		width: 140px;
	}
	.search input::placeholder {
		color: var(--muted);
	}
</style>

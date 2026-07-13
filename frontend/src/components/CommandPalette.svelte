<script lang="ts">
	import type { Command } from "../lib/commandPalette.svelte";

	interface Props {
		query: string;
		commands: Command[];
		onQueryChange: (value: string) => void;
		onRun: (command: Command) => void;
		onClose: () => void;
	}

	let { query, commands, onQueryChange, onRun, onClose }: Props = $props();

	let active = $state(0);
	let inputEl = $state<HTMLInputElement | null>(null);

	// Keep the active index in range as the filtered list changes.
	$effect(() => {
		if (active >= commands.length) active = Math.max(0, commands.length - 1);
	});

	$effect(() => {
		inputEl?.focus();
	});

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === "ArrowDown") {
			event.preventDefault();
			active = Math.min(commands.length - 1, active + 1);
		} else if (event.key === "ArrowUp") {
			event.preventDefault();
			active = Math.max(0, active - 1);
		} else if (event.key === "Enter") {
			event.preventDefault();
			const command = commands[active];
			if (command) onRun(command);
		} else if (event.key === "Escape") {
			event.preventDefault();
			onClose();
		}
	}
</script>

<div
	class="cmdk-overlay"
	role="presentation"
	onclick={(event) => {
		if (event.target === event.currentTarget) onClose();
	}}
>
	<div
		class="cmdk"
		role="dialog"
		aria-label="Command palette"
		aria-modal="true"
	>
		<input
			bind:this={inputEl}
			class="cmdk-input"
			type="text"
			aria-label="Command palette search"
			placeholder="Type a command…"
			value={query}
			oninput={(event) => onQueryChange((event.currentTarget as HTMLInputElement).value)}
			onkeydown={handleKeydown}
		/>
		<ul class="cmdk-list" role="listbox" aria-label="Commands">
			{#each commands as command, index (command.id)}
				<li>
					<button
						type="button"
						role="option"
						aria-selected={index === active}
						class="cmdk-item"
						class:active={index === active}
						onmousemove={() => (active = index)}
						onclick={() => onRun(command)}
					>
						<span>{command.label}</span>
						{#if command.hint}
							<span class="cmdk-hint">{command.hint}</span>
						{/if}
					</button>
				</li>
			{:else}
				<li class="cmdk-empty">No matching commands</li>
			{/each}
		</ul>
	</div>
</div>

<style>
	.cmdk-overlay {
		position: fixed;
		inset: 0;
		background: var(--overlay);
		display: flex;
		align-items: flex-start;
		justify-content: center;
		padding-top: 12vh;
		z-index: 400;
	}
	.cmdk {
		width: min(560px, calc(100vw - 32px));
		background: var(--surface-raised);
		border: 1px solid var(--line-strong);
		border-radius: var(--radius-lg);
		box-shadow: var(--shadow-lg);
		overflow: hidden;
	}
	.cmdk-input {
		width: 100%;
		background: transparent;
		border: none;
		border-bottom: 1px solid var(--line);
		outline: none;
		color: var(--ink);
		font-size: var(--text-lg);
		padding: 14px 16px;
	}
	.cmdk-list {
		list-style: none;
		margin: 0;
		padding: 6px;
		max-height: 320px;
		overflow-y: auto;
	}
	.cmdk-item {
		display: flex;
		align-items: center;
		justify-content: space-between;
		width: 100%;
		text-align: left;
		background: none;
		border: none;
		border-radius: var(--radius-sm);
		padding: 9px 12px;
		font-size: var(--text-sm);
		color: var(--ink);
	}
	.cmdk-item.active {
		background: var(--row-hover);
		color: var(--accent);
	}
	.cmdk-hint {
		font-size: var(--text-xs);
		color: var(--muted);
	}
	.cmdk-empty {
		padding: 12px;
		text-align: center;
		font-size: var(--text-sm);
		color: var(--muted);
	}
</style>

<script lang="ts">
	interface Props {
		open: boolean;
		onClose: () => void;
	}

	let { open, onClose }: Props = $props();

	const SHORTCUTS: { keys: string[]; label: string }[] = [
		{ keys: ["F"], label: "Focus filters" },
		{ keys: ["R"], label: "Refresh" },
		{ keys: ["J"], label: "Next notification" },
		{ keys: ["K"], label: "Previous notification" },
		{ keys: ["D"], label: "Dismiss focused" },
		{ keys: ["Enter"], label: "Open focused" },
		{ keys: ["/"], label: "Focus search" },
		{ keys: ["⌘", "K"], label: "Command palette" },
		{ keys: ["?"], label: "Toggle this panel" },
		{ keys: ["Esc"], label: "Blur / close" },
	];
</script>

{#if open}
	<dialog
		id="shortcuts-panel"
		class="shortcuts"
		aria-label="Keyboard shortcuts"
		open
		oncancel={(event) => {
			event.preventDefault();
			onClose();
		}}
	>
		<div class="shortcuts-header">
			<h2>Keyboard shortcuts</h2>
			<button type="button" aria-label="Close shortcuts" onclick={onClose}>✕</button>
		</div>
		<div class="kbd-grid">
			{#each SHORTCUTS as shortcut (shortcut.label)}
				<div class="kbd-row">
					<span class="kbd-keys">
						{#each shortcut.keys as key (key)}
							<kbd>{key}</kbd>
						{/each}
					</span>
					<span class="kbd-label">{shortcut.label}</span>
				</div>
			{/each}
		</div>
	</dialog>
{/if}

<style>
	.shortcuts {
		position: fixed;
		inset: 0;
		margin: auto;
		width: min(420px, calc(100vw - 32px));
		background: var(--surface-raised);
		color: var(--ink);
		border: 1px solid var(--line-strong);
		border-radius: var(--radius-lg);
		box-shadow: var(--shadow-lg);
		padding: 20px;
		z-index: 300;
	}
	.shortcuts::backdrop {
		background: var(--overlay);
	}
	.shortcuts-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 14px;
	}
	.shortcuts-header h2 {
		font-size: var(--text-lg);
		font-weight: 600;
	}
	.shortcuts-header button {
		background: none;
		border: none;
		color: var(--muted);
		font-size: var(--text-md);
	}
	.kbd-grid {
		display: grid;
		grid-template-columns: 1fr;
		gap: 8px;
	}
	.kbd-row {
		display: flex;
		align-items: center;
		gap: 12px;
	}
	.kbd-keys {
		display: inline-flex;
		gap: 4px;
		min-width: 84px;
	}
	.kbd-label {
		font-size: var(--text-sm);
		color: var(--ink-secondary);
	}
</style>

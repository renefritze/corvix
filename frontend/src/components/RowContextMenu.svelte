<script lang="ts">
	interface Props {
		x: number;
		y: number;
		onCreateRule: () => void;
	}

	let { x, y, onCreateRule }: Props = $props();
</script>

<div class="row-menu" style={`left: ${x}px; top: ${y}px`} role="menu">
	<button type="button" role="menuitem" onclick={onCreateRule}>
		Create ignore rule...
	</button>
</div>

<style>
	.row-menu {
		position: fixed;
		z-index: 200;
		min-width: 180px;
		background: var(--surface-raised);
		border: 1px solid var(--line-strong);
		border-radius: var(--radius-md);
		box-shadow: var(--shadow-md);
		overflow: hidden;
	}
	.row-menu button {
		width: 100%;
		text-align: left;
		border: 0;
		border-radius: 0;
		background: transparent;
		color: var(--ink);
		padding: 8px 12px;
		font-size: var(--text-sm);
	}
	.row-menu button:hover {
		background: var(--row-hover);
		color: var(--accent);
	}
</style>

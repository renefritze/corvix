<script lang="ts">
	import { ChevronDown, ChevronRight } from "@lucide/svelte";

	interface Props {
		name: string;
		total: number;
		unreadCount: number;
		readCount: number;
		isMarkingRead: boolean;
		isDismissingGroup: boolean;
		collapsed: boolean;
		colspan: number;
		onToggleCollapse: () => void;
		onMarkAllRead: () => void;
		onRemoveRead: () => void;
	}

	let {
		name,
		total,
		unreadCount,
		readCount,
		isMarkingRead,
		isDismissingGroup,
		collapsed,
		colspan,
		onToggleCollapse,
		onMarkAllRead,
		onRemoveRead,
	}: Props = $props();
</script>

<tr class="nt-group-row" data-testid="group-header-row">
	<td {colspan}>
		<div class="nt-group-content">
			<button
				type="button"
				class="nt-group-title"
				aria-expanded={!collapsed}
				aria-label={collapsed ? `Expand ${name}` : `Collapse ${name}`}
				onclick={onToggleCollapse}
			>
				{#if collapsed}
					<ChevronRight size={13} aria-hidden="true" />
				{:else}
					<ChevronDown size={13} aria-hidden="true" />
				{/if}
				<span>{name}</span>
				<span class="nt-group-count">({total})</span>
			</button>
			<div class="nt-group-actions">
				{#if readCount > 0}
					<button
						type="button"
						class="nt-group-btn"
						aria-label={`Dismiss all visible read notifications in ${name}`}
						disabled={isDismissingGroup}
						onclick={() => {
							if (isDismissingGroup) return;
							onRemoveRead();
						}}
					>
						Remove read ({readCount})
					</button>
				{/if}
				{#if unreadCount > 0}
					<button
						type="button"
						class="nt-group-btn"
						aria-label={`Mark all visible unread notifications in ${name} as read`}
						disabled={isMarkingRead}
						onclick={onMarkAllRead}
					>
						{isMarkingRead ? "Marking..." : `Mark all read (${unreadCount})`}
					</button>
				{/if}
			</div>
		</div>
	</td>
</tr>

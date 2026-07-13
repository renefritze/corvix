<script lang="ts">
	import { MoreHorizontal, X } from "@lucide/svelte";
	import type { DashboardItem } from "../types";

	interface Props {
		item: DashboardItem;
		onDismiss: (accountId: string, threadId: string) => void;
		onOpenTarget: (accountId: string, threadId: string) => void;
		onRequestIgnoreRule: (
			item: DashboardItem,
			position: { x: number; y: number },
		) => void;
		isPendingDismissal: boolean;
	}

	let { item, onDismiss, onOpenTarget, onRequestIgnoreRule, isPendingDismissal }: Props =
		$props();

	function relativeTime(iso: string): string {
		const diff = Date.now() - new Date(iso).getTime();
		const minutes = Math.floor(diff / 60_000);
		if (minutes < 60) return `${minutes}m ago`;
		const hours = Math.floor(minutes / 60);
		if (hours < 24) return `${hours}h ago`;
		const days = Math.floor(hours / 24);
		return `${days}d ago`;
	}

	const scoreLabel = $derived(item.score.toFixed(1));
	const updatedLabel = $derived(relativeTime(item.updated_at));
	const unreadStatusLabel = $derived(item.unread ? "Unread" : "Read");

	function handleOpenTarget() {
		if (!item.unread) return;
		onOpenTarget(item.account_id, item.thread_id);
	}

	function handleTitleClick() {
		handleOpenTarget();
	}

	function handleTitleAuxClick(event: MouseEvent) {
		if (event.button !== 1) return;
		handleOpenTarget();
	}

	function handleContextMenu(event: MouseEvent) {
		event.preventDefault();
		onRequestIgnoreRule(item, { x: event.clientX, y: event.clientY });
	}

	function handleMenuButtonClick(event: MouseEvent) {
		event.preventDefault();
		event.stopPropagation();
		const rect = (event.currentTarget as HTMLElement).getBoundingClientRect();
		onRequestIgnoreRule(item, { x: rect.left, y: rect.bottom + 4 });
	}
</script>

<tr
	data-account-id={item.account_id}
	data-thread-id={item.thread_id}
	tabindex="0"
	oncontextmenu={handleContextMenu}
	class="nt-row {item.unread ? 'unread' : 'read'}"
	class:dismissing={isPendingDismissal}
>
	<td class="col-status" aria-label={unreadStatusLabel}>
		<span class="nt-dot {item.unread ? 'on' : 'off'}" aria-hidden="true"></span>
	</td>
	<td class="col-title" data-label="Title">
		{#if item.web_url}
			<a
				href={item.web_url}
				target="_blank"
				rel="noopener noreferrer"
				class="nt-title-link"
				onclick={handleTitleClick}
				onauxclick={handleTitleAuxClick}
			>
				{item.subject_title}
			</a>
		{:else}
			<span class="nt-title-link">{item.subject_title}</span>
		{/if}
		<div class="nt-title-meta">
			{`${item.account_label} · ${scoreLabel} · ${updatedLabel} · ${item.subject_type} · ${item.reason}`}
		</div>
	</td>
	<td class="col-repository" data-label="Repository">
		<span class="nt-repo">{item.repository}</span>
	</td>
	<td class="col-type hide-mobile" data-label="Type">{item.subject_type}</td>
	<td class="col-reason hide-mobile" data-label="Reason">{item.reason}</td>
	<td class="col-score" data-label="Score">
		<span class="nt-score">{scoreLabel}</span>
	</td>
	<td class="col-updated" data-label="Updated">
		<span class="nt-updated" title={item.updated_at}>{updatedLabel}</span>
	</td>
	<td class="col-actions">
		<button
			type="button"
			class="nt-icon-btn nt-menu-btn"
			aria-label={`Notification actions for ${item.subject_title}`}
			onclick={handleMenuButtonClick}
		>
			<MoreHorizontal size={15} aria-hidden="true" />
		</button>
		<button
			type="button"
			class="nt-icon-btn nt-dismiss-btn"
			aria-label={`Dismiss ${item.subject_title}`}
			onclick={() => onDismiss(item.account_id, item.thread_id)}
		>
			<X size={15} aria-hidden="true" />
		</button>
	</td>
</tr>

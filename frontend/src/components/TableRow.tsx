import type { DashboardItem } from "../types";

function relativeTime(iso: string): string {
	const diff = Date.now() - new Date(iso).getTime();
	const minutes = Math.floor(diff / 60_000);
	if (minutes < 60) return `${minutes}m ago`;
	const hours = Math.floor(minutes / 60);
	if (hours < 24) return `${hours}h ago`;
	const days = Math.floor(hours / 24);
	return `${days}d ago`;
}

interface TableRowProps {
	readonly item: DashboardItem;
	readonly onDismiss: (accountId: string, threadId: string) => void;
	readonly onOpenTarget: (accountId: string, threadId: string) => void;
	readonly onRequestIgnoreRule: (
		item: DashboardItem,
		position: { x: number; y: number },
	) => void;
	readonly isPendingDismissal: boolean;
}

export function TableRow({
	item,
	onDismiss,
	onOpenTarget,
	onRequestIgnoreRule,
	isPendingDismissal,
}: TableRowProps) {
	const scoreLabel = item.score.toFixed(1);
	const updatedLabel = relativeTime(item.updated_at);
	const unreadStatusLabel = item.unread ? "Unread" : "Read";

	function handleOpenTarget() {
		if (!item.unread) return;
		onOpenTarget(item.account_id, item.thread_id);
	}

	function handleTitleClick() {
		handleOpenTarget();
	}

	function handleTitleAuxClick(e: MouseEvent) {
		if (e.button !== 1) return;
		handleOpenTarget();
	}

	function handleContextMenu(e: MouseEvent) {
		e.preventDefault();
		onRequestIgnoreRule(item, { x: e.clientX, y: e.clientY });
	}

	function handleMenuButtonClick(e: MouseEvent) {
		e.preventDefault();
		e.stopPropagation();
		const button = e.currentTarget as HTMLButtonElement;
		const rect = button.getBoundingClientRect();
		onRequestIgnoreRule(item, { x: rect.left, y: rect.bottom + 4 });
	}

	return (
		<tr
			data-account-id={item.account_id}
			data-thread-id={item.thread_id}
			tabIndex={0}
			onContextMenu={handleContextMenu as unknown as (e: Event) => void}
			class={[
				"notification-row",
				item.unread ? "unread" : "read",
				isPendingDismissal ? "dismissing" : "",
			]
				.filter(Boolean)
				.join(" ")}
		>
			<td class="col-status" aria-label={unreadStatusLabel}>
				<span
					class={`unread-dot ${item.unread ? "dot-unread" : "dot-read"}`}
					aria-hidden="true"
				/>
			</td>
			<td class="col-title" data-label="Title">
				{item.web_url ? (
					<a
						href={item.web_url}
						target="_blank"
						rel="noopener noreferrer"
						class="title-link"
						onClick={handleTitleClick as unknown as (e: Event) => void}
						onAuxClick={handleTitleAuxClick as unknown as (e: Event) => void}
					>
						{item.subject_title}
					</a>
				) : (
					<span class="title-link">{item.subject_title}</span>
				)}
				<div class="title-meta">
					{`${item.account_label} · ${scoreLabel} · ${updatedLabel} · ${item.subject_type} · ${item.reason}`}
				</div>
			</td>
			<td class="col-repository" data-label="Repository">
				<span class="repo-label">{item.repository}</span>
			</td>
			<td class="col-type hide-mobile" data-label="Type">
				{item.subject_type}
			</td>
			<td class="col-reason hide-mobile" data-label="Reason">
				{item.reason}
			</td>
			<td class="col-score" data-label="Score">
				<span class="score-value">{scoreLabel}</span>
			</td>
			<td class="col-updated" data-label="Updated">
				<span title={item.updated_at}>{updatedLabel}</span>
			</td>
			<td class="col-actions">
				<button
					type="button"
					class="row-menu-btn"
					aria-label={`Notification actions for ${item.subject_title}`}
					onClick={handleMenuButtonClick as unknown as (e: Event) => void}
				>
					⋯
				</button>
				<button
					type="button"
					class="dismiss-btn"
					aria-label={`Dismiss ${item.subject_title}`}
					onClick={() => onDismiss(item.account_id, item.thread_id)}
				>
					✕
				</button>
			</td>
		</tr>
	);
}

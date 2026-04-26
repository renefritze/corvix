import type { JSX } from "preact";
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

	function handleTitleClick(_e: JSX.TargetedMouseEvent<HTMLAnchorElement>) {
		handleOpenTarget();
	}

	function handleTitleAuxClick(e: JSX.TargetedMouseEvent<HTMLAnchorElement>) {
		if (e.button !== 1) return;
		handleOpenTarget();
	}

	function handleContextMenu(e: JSX.TargetedMouseEvent<HTMLTableRowElement>) {
		e.preventDefault();
		onRequestIgnoreRule(item, { x: e.clientX, y: e.clientY });
	}

	function handleMenuButtonClick(e: JSX.TargetedMouseEvent<HTMLButtonElement>) {
		e.preventDefault();
		e.stopPropagation();
		const rect = e.currentTarget.getBoundingClientRect();
		onRequestIgnoreRule(item, { x: rect.left, y: rect.bottom + 4 });
	}

	return (
		<tr
			data-account-id={item.account_id}
			data-thread-id={item.thread_id}
			tabIndex={0}
			onContextMenu={handleContextMenu}
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
						onClick={handleTitleClick}
						onAuxClick={handleTitleAuxClick}
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
					onClick={handleMenuButtonClick}
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

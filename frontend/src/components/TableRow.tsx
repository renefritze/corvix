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
	item: DashboardItem;
	onDismiss: (threadId: string) => void;
	onOpenTarget: (threadId: string) => void;
	isPendingDismissal: boolean;
}

export function TableRow({
	item,
	onDismiss,
	onOpenTarget,
	isPendingDismissal,
}: TableRowProps) {
	function handleOpenTarget() {
		if (!item.unread) return;
		onOpenTarget(item.thread_id);
	}

	function openInNewTab() {
		if (!item.web_url) return;
		window.open(item.web_url, "_blank", "noopener,noreferrer");
	}

	function handleTitleClick(e: MouseEvent) {
		e.preventDefault();
		openInNewTab();
		handleOpenTarget();
	}

	function handleTitleAuxClick(e: MouseEvent) {
		if (e.button !== 1) return;
		e.preventDefault();
		openInNewTab();
		handleOpenTarget();
	}

	return (
		<tr
			data-thread-id={item.thread_id}
			class={[
				"notification-row",
				item.unread ? "unread" : "read",
				isPendingDismissal ? "dismissing" : "",
			]
				.filter(Boolean)
				.join(" ")}
		>
			<td class="col-status" aria-hidden="true">
				<span class={`unread-dot ${item.unread ? "dot-unread" : "dot-read"}`} />
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
				<span class="score-value">{item.score.toFixed(1)}</span>
			</td>
			<td class="col-updated" data-label="Updated">
				<span title={item.updated_at}>{relativeTime(item.updated_at)}</span>
			</td>
			<td class="col-actions">
				<button
					type="button"
					class="dismiss-btn"
					aria-label={`Dismiss ${item.subject_title}`}
					onClick={() => onDismiss(item.thread_id)}
				>
					✕
				</button>
			</td>
		</tr>
	);
}

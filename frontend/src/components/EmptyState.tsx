import type { FilterState } from "../types";
import styles from "./EmptyState.module.css";

interface EmptyStateFilterContext {
	readonly unread: FilterState["unread"];
	readonly reason: string[];
	readonly repository: string;
}

interface EmptyStateProps {
	readonly hasFilters: boolean;
	readonly totalItems: number;
	readonly onClearFilters: () => void;
	readonly onRetry: () => void;
	readonly error?: string | null;
	readonly filterContext?: EmptyStateFilterContext;
}

export function EmptyState({
	hasFilters,
	totalItems,
	onClearFilters,
	onRetry,
	error,
	filterContext,
}: EmptyStateProps) {
	if (error) {
		return (
			<div class={[styles.emptyState, styles.errorState].join(" ")} data-testid="empty-state">
				<p class={styles.emptyTitle} data-testid="empty-title">Failed to load</p>
				<p class={styles.emptyBody} data-testid="empty-body">{error}</p>
				<button type="button" onClick={onRetry}>
					Retry
				</button>
			</div>
		);
	}

	if (hasFilters) {
		let title = "No results";
		let body = "No notifications match the current filters.";

		if (filterContext?.unread === "unread" && filterContext.repository !== "") {
			title = `No unread notifications in ${filterContext.repository}`;
			body = "You're all caught up for this repository.";
		} else if (filterContext?.repository) {
			title = `No notifications in ${filterContext.repository}`;
			body = "No notifications in this repository match your filters.";
		} else if (filterContext?.unread === "unread") {
			title = "No unread notifications";
			body = "You're all caught up for the current filters.";
		}

		return (
			<div class={styles.emptyState} data-testid="empty-state">
				<p class={styles.emptyTitle} data-testid="empty-title">{title}</p>
				<p class={styles.emptyBody} data-testid="empty-body">{body}</p>
				<button type="button" onClick={onClearFilters}>
					Clear filters
				</button>
			</div>
		);
	}

	if (totalItems === 0) {
		return (
			<div class={styles.emptyState} data-testid="empty-state">
				<p class={styles.emptyTitle} data-testid="empty-title">All clear</p>
				<p class={styles.emptyBody} data-testid="empty-body">No notifications in this dashboard.</p>
			</div>
		);
	}
	return (
		<div class={styles.emptyState} data-testid="empty-state">
			<p class={styles.emptyTitle} data-testid="empty-title">No results</p>
			<p class={styles.emptyBody} data-testid="empty-body">No notifications match the current filters.</p>
		</div>
	);
}

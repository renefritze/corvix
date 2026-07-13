<script lang="ts">
	import type { FilterState } from "../types";
	import CenteredNotice from "./CenteredNotice.svelte";

	interface FilterContext {
		unread: FilterState["unread"];
		reason: string[];
		repository: string;
	}

	interface Props {
		hasFilters: boolean;
		totalItems: number;
		onClearFilters: () => void;
		onRetry: () => void;
		error?: string | null;
		filterContext?: FilterContext;
	}

	let {
		hasFilters,
		totalItems,
		onClearFilters,
		onRetry,
		error = null,
		filterContext,
	}: Props = $props();

	interface Resolved {
		title: string;
		body: string;
		variant: "neutral" | "error";
		action: "retry" | "clear" | "none";
	}

	const resolved = $derived.by<Resolved>(() => {
		if (error) {
			return { title: "Failed to load", body: error, variant: "error", action: "retry" };
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
			return { title, body, variant: "neutral", action: "clear" };
		}
		if (totalItems === 0) {
			return {
				title: "All clear",
				body: "No notifications in this dashboard.",
				variant: "neutral",
				action: "none",
			};
		}
		return {
			title: "No results",
			body: "No notifications match the current filters.",
			variant: "neutral",
			action: "none",
		};
	});
</script>

<CenteredNotice title={resolved.title} body={resolved.body} variant={resolved.variant}>
	{#if resolved.action === "retry"}
		<button type="button" onclick={onRetry}>Retry</button>
	{:else if resolved.action === "clear"}
		<button type="button" onclick={onClearFilters}>Clear filters</button>
	{/if}
</CenteredNotice>

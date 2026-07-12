<script lang="ts">
	import { AlertTriangle, Clock, Hourglass } from "@lucide/svelte";
	import type { PollerStatus } from "../types";

	let { poller }: { poller: PollerStatus } = $props();

	function lastPollText(lastPollTime: string | null): string {
		if (!lastPollTime) return "";
		const timestamp = new Date(lastPollTime).getTime();
		if (Number.isNaN(timestamp)) return "";
		const delta = Math.max(0, Math.round((Date.now() - timestamp) / 1000));
		if (delta < 60) return `${delta}s ago`;
		if (delta < 3600) return `${Math.floor(delta / 60)}m ago`;
		return `${Math.floor(delta / 3600)}h ago`;
	}

	const lastUpdateText = $derived(lastPollText(poller.last_poll_time));
	const lastErrorTimeText = $derived(lastPollText(poller.last_error_time));
</script>

{#if poller.status === "error"}
	<div class="poller error" role="alert">
		<AlertTriangle size={15} class="poller-icon" aria-hidden="true" />
		<span class="poller-text">
			{poller.last_error
				? poller.last_error.split("\n").slice(-2).join(" ").trim()
				: "Poller encountered an error."}{lastErrorTimeText
				? ` (${lastErrorTimeText})`
				: ""}
		</span>
	</div>
{/if}

{#if poller.status === "unknown" || poller.status === "starting"}
	<div class="poller pending" role="status" aria-live="polite">
		<Hourglass size={15} class="poller-icon" aria-hidden="true" />
		<span class="poller-text">Waiting for poller to start...</span>
	</div>
{/if}

{#if poller.stale && poller.status !== "error"}
	<div class="poller stale" role="status" aria-live="polite">
		<Clock size={15} class="poller-icon" aria-hidden="true" />
		<span class="poller-text">
			Data may be stale{lastUpdateText ? ` (last update ${lastUpdateText})` : ""}.
		</span>
	</div>
{/if}

{#each poller.account_errors ?? [] as accountError (accountError.account_id)}
	<div class="poller error" role="alert">
		<AlertTriangle size={15} class="poller-icon" aria-hidden="true" />
		<span class="poller-text">
			<strong>{accountError.account_label}</strong>:
			{accountError.error || "Failed to fetch notifications."}
		</span>
	</div>
{/each}

<style>
	.poller {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 7px 16px;
		font-size: var(--text-sm);
		border-bottom: 1px solid var(--line);
	}
	.poller :global(.poller-icon) {
		flex-shrink: 0;
	}
	.poller.error {
		color: var(--danger);
		background: color-mix(in srgb, var(--danger) 8%, transparent);
	}
	.poller.pending {
		color: var(--ink-secondary);
		background: var(--bg-subtle);
	}
	.poller.stale {
		color: var(--warning);
		background: color-mix(in srgb, var(--warning) 8%, transparent);
	}
	.poller-text {
		min-width: 0;
	}
</style>

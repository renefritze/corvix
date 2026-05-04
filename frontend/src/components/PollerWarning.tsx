import type { PollerStatus } from "../types";

interface PollerWarningProps {
	readonly poller: PollerStatus;
}

function lastPollText(lastPollTime: string | null): string {
	if (!lastPollTime) return "";
	const delta = Math.round(
		(Date.now() - new Date(lastPollTime).getTime()) / 1000,
	);
	if (delta < 60) return `${delta}s ago`;
	if (delta < 3600) return `${Math.round(delta / 60)}m ago`;
	return `${Math.round(delta / 3600)}h ago`;
}

export function PollerWarning({ poller }: PollerWarningProps) {
	const { status, last_error: lastError, stale, last_poll_time } = poller;

	if (status === "error") {
		const message = lastError
			? lastError.split("\n").slice(-2).join(" ").trim()
			: "Poller encountered an error.";
		return (
			<div class="poller-warning poller-warning--error" role="alert">
				<span class="poller-warning__icon" aria-hidden="true">
					⚠
				</span>
				<span class="poller-warning__text">{message}</span>
			</div>
		);
	}

	if (status === "unknown" || status === "starting") {
		return (
			<div class="poller-warning poller-warning--pending" role="alert">
				<span class="poller-warning__icon" aria-hidden="true">
					⏳
				</span>
				<span class="poller-warning__text">Waiting for poller to start...</span>
			</div>
		);
	}

	if (stale) {
		return (
			<div class="poller-warning poller-warning--stale" role="alert">
				<span class="poller-warning__icon" aria-hidden="true">
					🕐
				</span>
				<span class="poller-warning__text">
					Data may be stale
					{last_poll_time
						? ` (last update ${lastPollText(last_poll_time)})`
						: ""}
					.
				</span>
			</div>
		);
	}

	return null;
}

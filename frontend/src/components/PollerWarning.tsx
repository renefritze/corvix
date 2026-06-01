import type { AccountError, PollerStatus } from "../types";
import styles from "./PollerWarning.module.css";

interface PollerWarningProps {
	readonly poller: PollerStatus;
}

function lastPollText(lastPollTime: string | null): string {
	if (!lastPollTime) return "";
	const timestamp = new Date(lastPollTime).getTime();
	if (Number.isNaN(timestamp)) return "";
	const delta = Math.max(0, Math.round((Date.now() - timestamp) / 1000));
	if (delta < 60) return `${delta}s ago`;
	if (delta < 3600) return `${Math.floor(delta / 60)}m ago`;
	return `${Math.floor(delta / 3600)}h ago`;
}

function AccountErrorBanner({ accountError }: { accountError: AccountError }) {
	const message = accountError.error || "Failed to fetch notifications.";
	return (
		<div class={[styles.pollerWarning, styles.error].join(" ")} role="alert">
			<span class={styles.icon} aria-hidden="true">
				⚠
			</span>
			<span class={styles.text}>
				<strong>{accountError.account_label}</strong>: {message}
			</span>
		</div>
	);
}

export function PollerWarning({ poller }: PollerWarningProps) {
	const {
		status,
		last_error: lastError,
		last_error_time: lastErrorTime,
		stale,
		last_poll_time,
		account_errors: accountErrors,
	} = poller;
	const lastUpdateText = lastPollText(last_poll_time);
	const lastErrorTimeText = lastPollText(lastErrorTime);

	return (
		<>
			{status === "error" && (
				<div class={[styles.pollerWarning, styles.error].join(" ")} role="alert">
					<span class={styles.icon} aria-hidden="true">
						⚠
					</span>
					<span class={styles.text}>
						{lastError
							? lastError.split("\n").slice(-2).join(" ").trim()
							: "Poller encountered an error."}
						{lastErrorTimeText ? ` (${lastErrorTimeText})` : ""}
					</span>
				</div>
			)}

			{(status === "unknown" || status === "starting") && (
				<div
					class={[styles.pollerWarning, styles.pending].join(" ")}
					role="status"
					aria-live="polite"
				>
					<span class={styles.icon} aria-hidden="true">
						⏳
					</span>
					<span class={styles.text}>
						Waiting for poller to start...
					</span>
				</div>
			)}

			{stale && status !== "error" && (
				<div
					class={[styles.pollerWarning, styles.stale].join(" ")}
					role="status"
					aria-live="polite"
				>
					<span class={styles.icon} aria-hidden="true">
						🕐
					</span>
					<span class={styles.text}>
						Data may be stale
						{lastUpdateText ? ` (last update ${lastUpdateText})` : ""}.
					</span>
				</div>
			)}

			{accountErrors?.map((ae) => (
				<AccountErrorBanner key={ae.account_id} accountError={ae} />
			))}
		</>
	);
}

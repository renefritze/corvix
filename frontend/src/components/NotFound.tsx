import { route } from "preact-router";
import styles from "./EmptyState.module.css";

interface NotFoundProps {
	readonly url?: string;
}

/**
 * In-SPA 404 view shown for routes that don't match a known dashboard path.
 * Styled like {@link EmptyState} and offers a way back to the default
 * dashboard.
 */
export function NotFound({ url }: NotFoundProps) {
	return (
		<div class={[styles.emptyState, styles.errorState].join(" ")}>
			<p class={styles.emptyTitle}>Page not found</p>
			<p class={styles.emptyBody}>
				{url ? `No page matches ${url}.` : "This page doesn't exist."}
			</p>
			<button type="button" onClick={() => route("/", true)}>
				Back to dashboard
			</button>
		</div>
	);
}

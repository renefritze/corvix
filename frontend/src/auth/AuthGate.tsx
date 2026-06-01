import type { ComponentChildren } from "preact";
import { DEFAULT_UNAUTHORIZED_MESSAGE } from "../api";
import { useAuth } from "./AuthContext";
import appStyles from "../app.module.css";
import emptyStyles from "../components/EmptyState.module.css";

interface AuthGateProps {
	readonly children: ComponentChildren;
}

/**
 * Renders its children while the session is authenticated and a minimal login
 * UI otherwise. There is no backend authentication yet (issue B6), so the
 * "login" is currently a retry prompt; this is the seam where a real sign-in
 * form or OAuth redirect will live once auth is added server-side.
 */
export function AuthGate({ children }: AuthGateProps) {
	const { status, message, reset } = useAuth();

	if (status === "authenticated") {
		return <>{children}</>;
	}

	return (
		<div class={appStyles.shell} data-testid="app-shell">
			<main class={appStyles.board}>
				<div
					class={[emptyStyles.emptyState, emptyStyles.errorState, emptyStyles.authGate].join(" ")}
					data-testid="empty-state"
					role="alert"
				>
					<p class={emptyStyles.emptyTitle} data-testid="empty-title">Sign in required</p>
					<p class={emptyStyles.emptyBody} data-testid="empty-body">{message ?? DEFAULT_UNAUTHORIZED_MESSAGE}</p>
					<button type="button" onClick={reset}>
						Try again
					</button>
				</div>
			</main>
		</div>
	);
}

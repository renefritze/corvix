import type { ComponentChildren } from "preact";
import { useAuth } from "./AuthContext";

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
		<div class="shell">
			<main class="board">
				<div class="empty-state error-state auth-gate" role="alert">
					<p class="empty-title">Sign in required</p>
					<p class="empty-body">
						{message ?? "Your session has expired or you are not signed in."}
					</p>
					<button type="button" onClick={reset}>
						Try again
					</button>
				</div>
			</main>
		</div>
	);
}

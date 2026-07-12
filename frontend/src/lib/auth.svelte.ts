/**
 * Frontend session state. Starts `authenticated` and only flips to
 * `unauthenticated` after the API layer reports a 401/403 (see
 * {@link setUnauthorizedHandler}), even when the originating call swallows the
 * thrown {@link UnauthorizedError}. This is the seam a real sign-in flow builds
 * on without rewiring every call site.
 */
import { type UnauthorizedError, setUnauthorizedHandler } from "../api";
import type { AuthStatus } from "../types";

export class AuthStore {
	status = $state<AuthStatus>("authenticated");
	message = $state<string | null>(null);
	#cleanup: () => void;

	constructor() {
		this.#cleanup = setUnauthorizedHandler((error: UnauthorizedError) => {
			this.signalUnauthenticated(error.message);
		});
	}

	signalUnauthenticated(message?: string): void {
		this.status = "unauthenticated";
		this.message = message ?? null;
	}

	reset(): void {
		this.status = "authenticated";
		this.message = null;
	}

	destroy(): void {
		this.#cleanup();
	}
}

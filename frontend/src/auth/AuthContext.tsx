import { createContext } from "preact";
import type { ComponentChildren } from "preact";
import {
	useCallback,
	useContext,
	useEffect,
	useMemo,
	useState,
} from "preact/hooks";
import { type UnauthorizedError, setUnauthorizedHandler } from "../api";
import type { AuthStatus } from "../types";

export interface AuthState {
	/**
	 * Current session status. Starts as `authenticated` and only flips to
	 * `unauthenticated` after the API rejects a request with 401/403.
	 */
	readonly status: AuthStatus;
	/** Message explaining why the session is unauthenticated, if known. */
	readonly message: string | null;
	/**
	 * Marks the session unauthenticated. Called automatically when the API
	 * layer reports a 401/403, but also available for an explicit sign-out once
	 * real auth lands.
	 */
	readonly signalUnauthenticated: (message?: string) => void;
	/**
	 * Optimistically returns to the authenticated state. Used by the "Try
	 * again" affordance: the next request re-checks with the backend and will
	 * flip back to unauthenticated if the session is still invalid.
	 */
	readonly reset: () => void;
}

const defaultState: AuthState = {
	status: "authenticated",
	message: null,
	signalUnauthenticated: () => {},
	reset: () => {},
};

const AuthContext = createContext<AuthState>(defaultState);

interface AuthProviderProps {
	readonly children: ComponentChildren;
}

/**
 * Holds the frontend's view of the session and bridges API-layer auth failures
 * into that state. This is intentionally minimal: it provides the hooks a real
 * authentication flow (token input, OAuth redirect) can build on without
 * touching every call site, per issue F10.
 */
export function AuthProvider({ children }: AuthProviderProps) {
	const [status, setStatus] = useState<AuthStatus>("authenticated");
	const [message, setMessage] = useState<string | null>(null);

	const signalUnauthenticated = useCallback((nextMessage?: string) => {
		setStatus("unauthenticated");
		setMessage(nextMessage ?? null);
	}, []);

	const reset = useCallback(() => {
		setStatus("authenticated");
		setMessage(null);
	}, []);

	// Any 401/403 from the API flips the app into the unauthenticated state,
	// even when the originating hook swallows the thrown UnauthorizedError.
	useEffect(
		() =>
			setUnauthorizedHandler((error: UnauthorizedError) => {
				signalUnauthenticated(error.message);
			}),
		[signalUnauthenticated],
	);

	const value = useMemo<AuthState>(
		() => ({ status, message, signalUnauthenticated, reset }),
		[status, message, signalUnauthenticated, reset],
	);

	return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/** Reads the current {@link AuthState} from the nearest {@link AuthProvider}. */
export function useAuth(): AuthState {
	return useContext(AuthContext);
}

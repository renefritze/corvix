import type { RuleSnippetsPayload, SnapshotPayload } from "./types";

export const DEFAULT_UNAUTHORIZED_MESSAGE =
	"Your session has expired or you are not signed in.";

/**
 * Raised when the API rejects a request because the session is not (or no
 * longer) authenticated. Carries the originating HTTP status so callers can
 * distinguish 401 (unauthenticated) from 403 (forbidden) if needed.
 *
 * This is the dedicated error type the rest of the app uses to drive auth
 * state; see {@link setUnauthorizedHandler} and the auth context provider.
 */
export class UnauthorizedError extends Error {
	readonly status: number;

	constructor(message = DEFAULT_UNAUTHORIZED_MESSAGE, status = 401) {
		super(message);
		this.name = "UnauthorizedError";
		this.status = status;
	}
}

type UnauthorizedHandler = (error: UnauthorizedError) => void;

let unauthorizedHandler: UnauthorizedHandler | null = null;

/**
 * Registers the single handler invoked whenever the API returns 401/403. The
 * auth provider subscribes here so that a rejected request flips the app into
 * the unauthenticated state even when the calling code swallows the thrown
 * {@link UnauthorizedError} (e.g. `useSnapshot` stores errors as strings).
 *
 * Returns an unsubscribe function that only clears the handler if it is still
 * the active one, so overlapping mounts don't wipe each other out.
 */
export function setUnauthorizedHandler(
	handler: UnauthorizedHandler | null,
): () => void {
	unauthorizedHandler = handler;
	return () => {
		if (unauthorizedHandler === handler) {
			unauthorizedHandler = null;
		}
	};
}

/** 401 (unauthenticated) and 403 (forbidden) are both treated as auth failures. */
function isAuthStatus(status: number): boolean {
	return status === 401 || status === 403;
}

/** Best-effort extraction of a `detail` string from a JSON error body. */
async function extractDetail(res: Response): Promise<string> {
	try {
		const payload = (await res.json()) as { detail?: unknown };
		if (typeof payload.detail === "string") {
			return payload.detail;
		}
	} catch {
		// Non-JSON response; fall back to status code.
	}
	return "";
}

/**
 * Always throws. 401/403 responses raise an {@link UnauthorizedError} and
 * notify the registered handler; any other status raises a generic error whose
 * message is produced by `format` (so each endpoint keeps its own wording).
 */
async function throwResponseError(
	res: Response,
	format: (status: number, detailSuffix: string) => string,
): Promise<never> {
	const detail = await extractDetail(res);
	if (isAuthStatus(res.status)) {
		const error = new UnauthorizedError(
			detail || DEFAULT_UNAUTHORIZED_MESSAGE,
			res.status,
		);
		unauthorizedHandler?.(error);
		throw error;
	}
	const suffix = detail ? `: ${detail}` : "";
	throw new Error(format(res.status, suffix));
}

export async function fetchSnapshot(
	dashboard?: string,
): Promise<SnapshotPayload> {
	const url = dashboard
		? `/api/v1/snapshot?dashboard=${encodeURIComponent(dashboard)}`
		: "/api/v1/snapshot";
	const res = await fetch(url);
	if (!res.ok) {
		await throwResponseError(
			res,
			(status, suffix) => `Snapshot fetch failed: ${status}${suffix}`,
		);
	}
	return res.json() as Promise<SnapshotPayload>;
}

/**
 * URL of the Server-Sent Events stream that pushes snapshot updates. The
 * frontend opens an {@link EventSource} against this endpoint and only falls
 * back to {@link fetchSnapshot} polling when SSE is unavailable.
 */
export function snapshotEventsUrl(dashboard?: string): string {
	return dashboard
		? `/api/v1/events?dashboard=${encodeURIComponent(dashboard)}`
		: "/api/v1/events";
}

export async function dismissNotification(
	accountId: string,
	threadId: string,
): Promise<void> {
	const res = await fetch(
		`/api/v1/notifications/${encodeURIComponent(accountId)}/${encodeURIComponent(threadId)}/dismiss`,
		{ method: "POST" },
	);
	if (!res.ok) {
		await throwResponseError(
			res,
			(status, suffix) => `Dismiss failed (${status})${suffix}`,
		);
	}
}

export async function markNotificationRead(
	accountId: string,
	threadId: string,
): Promise<void> {
	const res = await fetch(
		`/api/v1/notifications/${encodeURIComponent(accountId)}/${encodeURIComponent(threadId)}/mark-read`,
		{ method: "POST", keepalive: true },
	);
	if (!res.ok) {
		await throwResponseError(
			res,
			(status, suffix) => `Mark read failed: ${status}${suffix}`,
		);
	}
}

export async function fetchRuleSnippets(
	accountId: string,
	threadId: string,
	dashboard?: string,
): Promise<RuleSnippetsPayload> {
	const query = dashboard ? `?dashboard=${encodeURIComponent(dashboard)}` : "";
	const res = await fetch(
		`/api/v1/notifications/${encodeURIComponent(accountId)}/${encodeURIComponent(threadId)}/rule-snippets${query}`,
	);
	if (!res.ok) {
		await throwResponseError(
			res,
			(status, suffix) => `Rule snippets fetch failed (${status})${suffix}`,
		);
	}
	return res.json() as Promise<RuleSnippetsPayload>;
}

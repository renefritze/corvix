import type { RuleSnippetsPayload, SnapshotPayload } from "./types";

export async function fetchSnapshot(
	dashboard?: string,
): Promise<SnapshotPayload> {
	const url = dashboard
		? `/api/snapshot?dashboard=${encodeURIComponent(dashboard)}`
		: "/api/snapshot";
	const res = await fetch(url);
	if (!res.ok) throw new Error(`Snapshot fetch failed: ${res.status}`);
	return res.json() as Promise<SnapshotPayload>;
}

export async function dismissNotification(
	accountId: string,
	threadId: string,
): Promise<void> {
	const res = await fetch(
		`/api/notifications/${encodeURIComponent(accountId)}/${encodeURIComponent(threadId)}/dismiss`,
		{ method: "POST" },
	);
	if (!res.ok) {
		let detail = "";
		try {
			const payload = (await res.json()) as { detail?: unknown };
			if (typeof payload.detail === "string") {
				detail = payload.detail;
			}
		} catch {
			// Non-JSON response; fall back to status code.
		}
		const suffix = detail ? `: ${detail}` : "";
		throw new Error(`Dismiss failed (${res.status})${suffix}`);
	}
}

export async function markNotificationRead(
	accountId: string,
	threadId: string,
): Promise<void> {
	const res = await fetch(
		`/api/notifications/${encodeURIComponent(accountId)}/${encodeURIComponent(threadId)}/mark-read`,
		{ method: "POST", keepalive: true },
	);
	if (!res.ok) throw new Error(`Mark read failed: ${res.status}`);
}

export async function fetchRuleSnippets(
	accountId: string,
	threadId: string,
	dashboard?: string,
): Promise<RuleSnippetsPayload> {
	const query = dashboard ? `?dashboard=${encodeURIComponent(dashboard)}` : "";
	const res = await fetch(
		`/api/notifications/${encodeURIComponent(accountId)}/${encodeURIComponent(threadId)}/rule-snippets${query}`,
	);
	if (!res.ok) {
		let detail = "";
		try {
			const payload = (await res.json()) as { detail?: unknown };
			if (typeof payload.detail === "string") {
				detail = payload.detail;
			}
		} catch {
			// Non-JSON response; fall back to status code.
		}
		const suffix = detail ? `: ${detail}` : "";
		throw new Error(`Rule snippets fetch failed (${res.status})${suffix}`);
	}
	return res.json() as Promise<RuleSnippetsPayload>;
}

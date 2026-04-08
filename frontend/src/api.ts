import type { SnapshotPayload } from "./types";

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

export async function dismissNotification(threadId: string): Promise<void> {
	const res = await fetch(
		`/api/notifications/${encodeURIComponent(threadId)}/dismiss`,
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

export async function markNotificationRead(threadId: string): Promise<void> {
	const res = await fetch(
		`/api/notifications/${encodeURIComponent(threadId)}/mark-read`,
		{ method: "POST", keepalive: true },
	);
	if (!res.ok) throw new Error(`Mark read failed: ${res.status}`);
}

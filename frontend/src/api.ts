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
	if (!res.ok) throw new Error(`Dismiss failed: ${res.status}`);
}

export async function markNotificationRead(threadId: string): Promise<void> {
	const res = await fetch(
		`/api/notifications/${encodeURIComponent(threadId)}/mark-read`,
		{ method: "POST", keepalive: true },
	);
	if (!res.ok) throw new Error(`Mark read failed: ${res.status}`);
}

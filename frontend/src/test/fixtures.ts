import type { DashboardItem, SnapshotPayload } from "../types";

export function makeItem(
	overrides: Partial<DashboardItem> = {},
): DashboardItem {
	return {
		thread_id: "thread-1",
		repository: "org/repo-a",
		reason: "mention",
		subject_type: "PullRequest",
		subject_title: "Review API changes",
		unread: true,
		updated_at: "2026-04-09T10:00:00Z",
		score: 90,
		web_url: "https://github.com/org/repo-a/pull/1",
		matched_rules: [],
		actions_taken: [],
		...overrides,
	};
}

export function makeSnapshot(
	overrides: Partial<SnapshotPayload> = {},
): SnapshotPayload {
	const items = [makeItem()];
	return {
		name: "overview",
		include_read: true,
		sort_by: "score",
		descending: true,
		generated_at: "2026-04-09T10:00:00Z",
		groups: [{ name: "org/repo-a", items }],
		total_items: items.length,
		summary: {
			unread_items: 1,
			read_items: 0,
			group_count: 1,
			repository_count: 1,
			reason_count: 1,
		},
		dashboard_names: ["overview", "triage"],
		notifications_config: null,
		...overrides,
	};
}

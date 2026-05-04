export interface DashboardItem {
	account_id: string;
	account_label: string;
	thread_id: string;
	repository: string;
	reason: string;
	subject_type: string;
	subject_title: string;
	unread: boolean;
	updated_at: string;
	score: number;
	web_url: string | null;
	matched_rules: string[];
	actions_taken: string[];
}

export interface DashboardGroup {
	name: string;
	items: DashboardItem[];
}

export interface DashboardSummary {
	unread_items: number;
	read_items: number;
	group_count: number;
	repository_count: number;
	reason_count: number;
}

export interface BrowserTabNotificationsConfig {
	enabled: boolean;
	max_per_cycle: number;
	cooldown_seconds: number;
}

export interface NotificationsConfig {
	enabled: boolean;
	browser_tab: BrowserTabNotificationsConfig;
}

export interface PollerStatus {
	status: string;
	last_poll_time: string | null;
	last_error: string | null;
	last_error_time: string | null;
	stale: boolean;
}

export interface SnapshotPayload {
	name: string;
	include_read: boolean;
	sort_by: string;
	descending: boolean;
	generated_at: string | null;
	groups: DashboardGroup[];
	total_items: number;
	summary: DashboardSummary;
	dashboard_names: string[];
	poller: PollerStatus;
	notifications_config: NotificationsConfig | null;
}

export interface RuleSnippetsPayload {
	dashboard_name: string;
	dashboard_ignore_rule_snippet: string;
	global_exclude_rule_snippet: string;
	dashboard_ignore_rule_with_context_snippet: string | null;
	global_exclude_rule_with_context_snippet: string | null;
	has_context: boolean;
}

export type SortColumn =
	| "subject_title"
	| "repository"
	| "subject_type"
	| "reason"
	| "score"
	| "updated_at";
export type SortDirection = "asc" | "desc";
export type ResizableSortColumn = Exclude<SortColumn, "subject_title">;
export type ColumnWidths = Record<ResizableSortColumn, number>;

export interface FilterState {
	unread: "all" | "unread" | "read";
	reason: string;
	repository: string;
}

export function notificationKey(
	item: Pick<DashboardItem, "account_id" | "thread_id">,
): string {
	return `${item.account_id}:${item.thread_id}`;
}

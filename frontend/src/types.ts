export interface DashboardItem {
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
	notifications_config: NotificationsConfig | null;
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

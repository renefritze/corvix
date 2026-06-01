import type { components } from "./api-types.gen";

/**
 * API payload types. These are aliases for the schemas in
 * {@link ./api-types.gen.ts}, which is code-generated from the backend's
 * OpenAPI document (`frontend/openapi.json`, produced by
 * `scripts/export_openapi.py` from the Litestar route handlers). Treat the
 * Python response dataclasses in `corvix.web.schemas` as the single source of
 * truth: run `make gen-types` after changing them, never edit the API shapes
 * here by hand. `api-types.gen.ts` is regenerated from the committed
 * `openapi.json` during `npm run build` (so it is gitignored, not committed); a
 * CI drift check fails the build if `openapi.json` falls out of sync with the
 * backend schema.
 */
type Schemas = components["schemas"];

export type DashboardItem = Schemas["DashboardItemResponse"];
export type DashboardGroup = Schemas["DashboardGroupResponse"];
export type DashboardSummary = Schemas["DashboardSummaryResponse"];
export type BrowserTabNotificationsConfig =
	Schemas["BrowserTabNotificationsConfigResponse"];
export type NotificationsConfig = Schemas["NotificationsConfigResponse"];
export type PollerStatus = Schemas["PollerStatusResponse"];
export type AccountError = Schemas["AccountErrorResponse"];
export type SnapshotPayload = Schemas["SnapshotResponse"];
export type RuleSnippetsPayload = Schemas["RuleSnippetsResponse"];

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
	reason: string[];
	repository: string;
}

/**
 * Session state as understood by the frontend. Defaults to `authenticated`
 * until the API reports otherwise (today there is no backend auth, so this is
 * effectively always authenticated; see issue B6). The scaffold exists so that
 * adding real authentication does not require rewiring the component tree.
 */
export type AuthStatus = "authenticated" | "unauthenticated";

export function notificationKey(
	item: Pick<DashboardItem, "account_id" | "thread_id">,
): string {
	return `${item.account_id}:${item.thread_id}`;
}

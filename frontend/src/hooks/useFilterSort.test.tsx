import { renderHook } from "@testing-library/preact";
import { beforeEach, describe, expect, it } from "vitest";
import { setPath } from "../test/http";
import type { SnapshotPayload } from "../types";
import { useFilterSort } from "./useFilterSort";

const baseSnapshot: SnapshotPayload = {
	name: "overview",
	include_read: true,
	sort_by: "score",
	descending: true,
	generated_at: null,
	groups: [],
	total_items: 0,
	summary: {
		unread_items: 0,
		read_items: 0,
		group_count: 0,
		repository_count: 0,
		reason_count: 0,
	},
	dashboard_names: [],
	poller: {
		status: "ok",
		last_poll_time: null,
		last_error: null,
		last_error_time: null,
		stale: false,
	},
	notifications_config: null,
};

describe("useFilterSort", () => {
	beforeEach(() => {
		setPath("/");
	});

	it("seeds sort from snapshot configuration", () => {
		const overrides: Partial<SnapshotPayload> = {
			sort_by: "title",
			descending: false,
		};
		const snapshot = { ...baseSnapshot, ...overrides };
		const { result } = renderHook(() => useFilterSort(snapshot));

		expect(result.current.sortColumn).toBe("subject_title");
		expect(result.current.sortDirection).toBe("asc");
	});

	it("locks the unread filter to unread-only when read is excluded", () => {
		const snapshot = { ...baseSnapshot, include_read: false };
		const { result } = renderHook(() => useFilterSort(snapshot));

		expect(result.current.dashboardAllowsRead).toBe(false);
		expect(result.current.effectiveUnreadFilter).toBe("unread");
	});

	it("seeds sort from the URL query, overriding the configured order", () => {
		setPath("/?sort=repository&dir=asc");
		const { result } = renderHook(() => useFilterSort(baseSnapshot));

		expect(result.current.sortColumn).toBe("repository");
		expect(result.current.sortDirection).toBe("asc");
	});

	it("seeds filters from the URL query", () => {
		setPath("/?unread=unread&reason=mention,subscribed&repository=org/repo");
		const { result } = renderHook(() => useFilterSort(baseSnapshot));

		expect(result.current.filters).toEqual({
			unread: "unread",
			reason: ["mention", "subscribed"],
			repository: "org/repo",
		});
	});
});

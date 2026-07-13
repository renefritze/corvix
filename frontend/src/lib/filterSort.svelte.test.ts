import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { FilterSortStore } from "./filterSort.svelte";
import { Router } from "./router.svelte";
import { makeSnapshot } from "../test/fixtures";
import type { SnapshotPayload } from "../types";

function make(path = "/", snapshot: SnapshotPayload | null = makeSnapshot()) {
	history.pushState({}, "", path);
	const router = new Router();
	return { router, store: new FilterSortStore(router, () => snapshot) };
}

describe("FilterSortStore", () => {
	beforeEach(() => history.pushState({}, "", "/"));
	afterEach(() => history.pushState({}, "", "/"));

	it("seeds sort from the snapshot configuration", () => {
		const { store } = make(
			"/",
			makeSnapshot({ sort_by: "title", descending: false }),
		);
		expect(store.sortColumn).toBe("subject_title");
		expect(store.sortDirection).toBe("asc");
	});

	it.each([
		["repository", "repository"],
		["subject_type", "subject_type"],
		["reason", "reason"],
		["updated_at", "updated_at"],
		["unknown", "score"],
	] as const)("maps dashboard sort_by %s to column %s", (sortBy, column) => {
		const { store } = make("/", makeSnapshot({ sort_by: sortBy }));
		expect(store.sortColumn).toBe(column);
	});

	it("seeds sort from the URL query, overriding the snapshot", () => {
		const { store } = make("/?sort=repository&dir=asc");
		expect(store.sortColumn).toBe("repository");
		expect(store.sortDirection).toBe("asc");
	});

	it("exposes and forwards filter state", () => {
		const { store } = make(
			"/?unread=unread&reason=mention,subscribed&repository=org/repo",
		);
		expect(store.filterState).toEqual({
			unread: "unread",
			reason: ["mention", "subscribed"],
			repository: "org/repo",
		});
	});

	it("forwards setFilter, clearFilters and handleSort to the inner stores", () => {
		const { router, store } = make("/");
		store.setFilter("repository", "org/repo");
		expect(router.query.get("repository")).toBe("org/repo");
		store.handleSort("reason");
		expect(router.query.get("sort")).toBe("reason");
		store.clearFilters();
		expect(router.query.get("repository")).toBeNull();
	});

	it("allows read when the snapshot includes read notifications", () => {
		const { store } = make("/", makeSnapshot({ include_read: true }));
		expect(store.dashboardAllowsRead).toBe(true);
	});

	it("defaults dashboardAllowsRead to true when no snapshot", () => {
		const { store } = make("/", null);
		expect(store.dashboardAllowsRead).toBe(true);
		expect(store.sortColumn).toBe("score");
		expect(store.sortDirection).toBe("desc");
	});

	it("locks the unread filter to unread when read is excluded", () => {
		const { store } = make("/", makeSnapshot({ include_read: false }));
		expect(store.dashboardAllowsRead).toBe(false);
		expect(store.effectiveUnreadFilter).toBe("unread");
	});

	it("passes through the unread filter when read is allowed", () => {
		const { store } = make("/?unread=read", makeSnapshot({ include_read: true }));
		expect(store.effectiveUnreadFilter).toBe("read");
	});

	it("keeps an explicit unread selection when read is excluded", () => {
		const { store } = make(
			"/?unread=unread",
			makeSnapshot({ include_read: false }),
		);
		expect(store.effectiveUnreadFilter).toBe("unread");
	});
});

import { afterEach, describe, expect, it, vi } from "vitest";
import * as api from "../api";
import { makeItem } from "../test/fixtures";
import { MarkReadStore } from "./markRead.svelte";

describe("MarkReadStore", () => {
	afterEach(() => {
		vi.restoreAllMocks();
	});

	function make() {
		const onRefresh = vi.fn().mockResolvedValue(undefined);
		const onError = vi.fn();
		const store = new MarkReadStore(onRefresh, onError);
		return { store, onRefresh, onError };
	}

	it("marks a single thread read and refreshes", async () => {
		const spy = vi.spyOn(api, "markNotificationRead").mockResolvedValue();
		const { store, onRefresh, onError } = make();

		store.openTarget("primary", "t-1");
		await vi.waitFor(() => expect(onRefresh).toHaveBeenCalledTimes(1));

		expect(spy).toHaveBeenCalledWith("primary", "t-1");
		expect(onError).not.toHaveBeenCalled();
	});

	it("reports an error when a single mark-read fails", async () => {
		vi.spyOn(api, "markNotificationRead").mockRejectedValue(
			new Error("boom"),
		);
		const { store, onRefresh, onError } = make();

		store.openTarget("primary", "t-1");
		await vi.waitFor(() => expect(onError).toHaveBeenCalledWith("boom"));

		expect(onRefresh).not.toHaveBeenCalled();
	});

	it("falls back to a generic message for a non-Error rejection", async () => {
		vi.spyOn(api, "markNotificationRead").mockRejectedValue("nope");
		const { store, onError } = make();

		store.openTarget("primary", "t-1");
		await vi.waitFor(() =>
			expect(onError).toHaveBeenCalledWith("Mark read failed"),
		);
	});

	it("marks only unread group items, tracks progress, and refreshes", async () => {
		const resolvers: Array<() => void> = [];
		vi.spyOn(api, "markNotificationRead").mockImplementation(
			() => new Promise<void>((resolve) => resolvers.push(resolve)),
		);
		const { store, onRefresh, onError } = make();
		const group = [
			makeItem({ thread_id: "u-1", unread: true }),
			makeItem({ thread_id: "u-2", unread: true }),
			makeItem({ thread_id: "r-1", unread: false }),
		];

		store.markGroupRead("group-a", group);

		expect(store.markingGroupNames.has("group-a")).toBe(true);
		expect(api.markNotificationRead).toHaveBeenCalledTimes(2);
		expect(api.markNotificationRead).toHaveBeenCalledWith("primary", "u-1");
		expect(api.markNotificationRead).not.toHaveBeenCalledWith(
			"primary",
			"r-1",
		);

		for (const resolve of resolvers) resolve();
		await vi.waitFor(() =>
			expect(store.markingGroupNames.has("group-a")).toBe(false),
		);
		await vi.waitFor(() => expect(onRefresh).toHaveBeenCalledTimes(1));
		expect(onError).not.toHaveBeenCalled();
	});

	it("reports the failure count when group items fail (plural)", async () => {
		vi.spyOn(api, "markNotificationRead").mockRejectedValue(
			new Error("500"),
		);
		const { store, onError } = make();
		const group = [
			makeItem({ thread_id: "u-1", unread: true }),
			makeItem({ thread_id: "u-2", unread: true }),
		];

		store.markGroupRead("group-a", group);
		await vi.waitFor(() =>
			expect(onError).toHaveBeenCalledWith(
				"Mark all read failed for 2 notifications",
			),
		);
	});

	it("uses the singular message for a single failure", async () => {
		vi.spyOn(api, "markNotificationRead").mockRejectedValue(
			new Error("500"),
		);
		const { store, onError } = make();
		const group = [makeItem({ thread_id: "u-1", unread: true })];

		store.markGroupRead("group-a", group);
		await vi.waitFor(() =>
			expect(onError).toHaveBeenCalledWith(
				"Mark all read failed for 1 notification",
			),
		);
	});

	it("does nothing when a group has no unread items", () => {
		const spy = vi.spyOn(api, "markNotificationRead").mockResolvedValue();
		const { store, onRefresh } = make();

		store.markGroupRead("empty", [makeItem({ unread: false })]);

		expect(spy).not.toHaveBeenCalled();
		expect(onRefresh).not.toHaveBeenCalled();
		expect(store.markingGroupNames.size).toBe(0);
	});
});

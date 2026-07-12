import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../api";
import { root } from "../test/runes.svelte";
import { DismissStore } from "./dismiss.svelte";

describe("DismissStore", () => {
	let dispose: (() => void) | undefined;

	beforeEach(() => vi.useFakeTimers());
	afterEach(() => {
		dispose?.();
		dispose = undefined;
		vi.useRealTimers();
	});

	function make(threadIds: Set<string> = new Set(["primary:1"])) {
		const onRefresh = vi.fn().mockResolvedValue(undefined);
		const onError = vi.fn();
		const { value: store, dispose: d } = root(() => {
			const s = new DismissStore(onRefresh, onError, () => threadIds);
			s.bind();
			return s;
		});
		dispose = d;
		return { store, onRefresh, onError };
	}

	it("hides a pending thread and shows in the count", () => {
		const { store } = make();
		store.dismiss("primary", "1");
		expect(store.count).toBe(1);
		expect(store.hiddenThreadIds.has("primary:1")).toBe(true);
	});

	it("commits after 3s, calling the API and refresh", async () => {
		const spy = vi.spyOn(api, "dismissNotification").mockResolvedValue();
		const { store, onRefresh } = make();
		store.dismiss("primary", "1");
		await vi.advanceTimersByTimeAsync(3000);
		expect(spy).toHaveBeenCalledWith("primary", "1");
		expect(onRefresh).toHaveBeenCalled();
		expect(store.count).toBe(0);
	});

	it("undo cancels a pending dismissal before commit", () => {
		const spy = vi.spyOn(api, "dismissNotification").mockResolvedValue();
		const { store } = make();
		store.dismiss("primary", "1");
		store.undo("primary", "1");
		vi.advanceTimersByTime(3000);
		expect(spy).not.toHaveBeenCalled();
		expect(store.count).toBe(0);
	});

	it("undoAll clears every pending dismissal", () => {
		const { store } = make(new Set(["primary:1", "primary:2"]));
		store.dismiss("primary", "1");
		store.dismiss("primary", "2");
		expect(store.count).toBe(2);
		store.undoAll();
		expect(store.count).toBe(0);
	});

	it("reports an error when the API rejects and un-commits", async () => {
		vi.spyOn(api, "dismissNotification").mockRejectedValue(new Error("boom"));
		const { store, onError } = make();
		store.dismiss("primary", "1");
		await vi.advanceTimersByTimeAsync(3000);
		expect(onError).toHaveBeenCalledWith("boom");
	});
});

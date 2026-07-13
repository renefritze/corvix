import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../api";
import { makeSnapshot } from "../test/fixtures";
import { root } from "../test/runes.svelte";
import type { SnapshotPayload } from "../types";
import { SnapshotStore } from "./snapshot.svelte";

describe("SnapshotStore (polling path, no EventSource)", () => {
	let dispose: (() => void) | undefined;

	function make(dashboard: string | undefined = undefined) {
		const { value, dispose: d } = root(() => {
			const s = new SnapshotStore();
			s.bind(() => dashboard);
			return s;
		});
		dispose = d;
		return value;
	}

	afterEach(() => {
		dispose?.();
		dispose = undefined;
		vi.restoreAllMocks();
		vi.useRealTimers();
	});

	it("performs the initial load and clears loading", async () => {
		const spy = vi
			.spyOn(api, "fetchSnapshot")
			.mockResolvedValue(makeSnapshot({ name: "overview" }));
		const store = make("overview");

		await vi.waitFor(() => expect(store.snapshot?.name).toBe("overview"));
		expect(store.loading).toBe(false);
		expect(store.error).toBeNull();
		expect(spy).toHaveBeenCalledWith("overview");
	});

	it("stores the error message on a failed load", async () => {
		vi.spyOn(api, "fetchSnapshot").mockRejectedValue(new Error("boom"));
		const store = make();

		await vi.waitFor(() => expect(store.error).toBe("boom"));
		expect(store.loading).toBe(false);
	});

	it("falls back to 'Unknown error' for non-Error rejections", async () => {
		vi.spyOn(api, "fetchSnapshot").mockRejectedValue("nope");
		const store = make();

		await vi.waitFor(() => expect(store.error).toBe("Unknown error"));
	});

	it("marks manualRefreshing during a refresh() flight", async () => {
		let resolveInitial!: (p: SnapshotPayload) => void;
		let resolveRefresh!: (p: SnapshotPayload) => void;
		vi.spyOn(api, "fetchSnapshot")
			.mockImplementationOnce(
				() => new Promise((r) => (resolveInitial = r)),
			)
			.mockImplementationOnce(
				() => new Promise((r) => (resolveRefresh = r)),
			);
		const store = make();

		resolveInitial(makeSnapshot({ name: "overview" }));
		await vi.waitFor(() => expect(store.snapshot?.name).toBe("overview"));

		const pending = store.refresh();
		expect(store.manualRefreshing).toBe(true);
		expect(store.refreshing).toBe(true);

		resolveRefresh(makeSnapshot({ name: "refreshed" }));
		await pending;
		expect(store.manualRefreshing).toBe(false);
		expect(store.refreshing).toBe(false);
	});

	it("coalesces a refresh requested while a load is in flight", async () => {
		let resolveInitial!: (p: SnapshotPayload) => void;
		const spy = vi
			.spyOn(api, "fetchSnapshot")
			.mockImplementationOnce(
				() => new Promise((r) => (resolveInitial = r)),
			)
			.mockResolvedValue(makeSnapshot({ name: "second" }));
		const store = make();

		// Initial load is in flight; a refresh queues one reload.
		store.refresh();
		expect(spy).toHaveBeenCalledTimes(1);

		resolveInitial(makeSnapshot({ name: "first" }));
		await vi.waitFor(() => expect(spy).toHaveBeenCalledTimes(2));
		await vi.waitFor(() => expect(store.snapshot?.name).toBe("second"));
	});

	it("polls every 15s and a queued manual outranks a queued auto", async () => {
		vi.useFakeTimers();
		let resolveInitial!: (p: SnapshotPayload) => void;
		let resolveAuto!: (p: SnapshotPayload) => void;
		let resolveManual!: (p: SnapshotPayload) => void;
		vi.spyOn(api, "fetchSnapshot")
			.mockImplementationOnce(
				() => new Promise((r) => (resolveInitial = r)),
			)
			.mockImplementationOnce(() => new Promise((r) => (resolveAuto = r)))
			.mockImplementationOnce(
				() => new Promise((r) => (resolveManual = r)),
			);
		const store = make("overview");

		resolveInitial(makeSnapshot({ name: "overview" }));
		await vi.waitFor(() => expect(store.snapshot?.name).toBe("overview"));

		// 15s elapses -> auto refresh fires (call #2, still in flight).
		await vi.advanceTimersByTimeAsync(15_000);
		expect(api.fetchSnapshot).toHaveBeenCalledTimes(2);
		expect(store.autoRefreshing).toBe(true);

		// A manual refresh while the auto is in flight queues with higher rank.
		store.refresh();
		expect(api.fetchSnapshot).toHaveBeenCalledTimes(2);

		// Auto resolves -> the queued manual (rank 2 > auto rank 1) runs next.
		resolveAuto(makeSnapshot({ name: "auto" }));
		await vi.waitFor(() =>
			expect(api.fetchSnapshot).toHaveBeenCalledTimes(3),
		);
		await vi.waitFor(() => expect(store.manualRefreshing).toBe(true));

		resolveManual(makeSnapshot({ name: "manual" }));
		await vi.waitFor(() => expect(store.snapshot?.name).toBe("manual"));
		expect(store.manualRefreshing).toBe(false);
	});

	it("a queued manual reassigns over an already-queued auto", async () => {
		vi.useFakeTimers();
		let resolveInitial!: (p: SnapshotPayload) => void;
		const spy = vi
			.spyOn(api, "fetchSnapshot")
			.mockImplementationOnce(
				() => new Promise((r) => (resolveInitial = r)),
			)
			.mockResolvedValue(makeSnapshot({ name: "reload" }));
		const store = make("overview");

		// Initial load is in flight; the 15s poll queues an auto reload.
		await vi.advanceTimersByTimeAsync(15_000);
		expect(spy).toHaveBeenCalledTimes(1);
		// A manual refresh outranks the queued auto (modeRank comparison).
		store.refresh();
		expect(spy).toHaveBeenCalledTimes(1);

		resolveInitial(makeSnapshot({ name: "first" }));
		await vi.waitFor(() => expect(spy).toHaveBeenCalledTimes(2));
		// The queued reload ran as a manual refresh.
		await vi.waitFor(() => expect(store.manualRefreshing).toBe(false));
		expect(store.snapshot?.name).toBe("reload");
	});

	it("an auto refresh does not outrank an already-queued manual", async () => {
		vi.useFakeTimers();
		let resolveInitial!: (p: SnapshotPayload) => void;
		const spy = vi
			.spyOn(api, "fetchSnapshot")
			.mockImplementationOnce(
				() => new Promise((r) => (resolveInitial = r)),
			)
			.mockResolvedValue(makeSnapshot({ name: "reload" }));
		const store = make("overview");

		// Queue a manual refresh while the initial load is in flight.
		store.refresh();
		// The 15s auto poll fires but must NOT downgrade the queued manual.
		await vi.advanceTimersByTimeAsync(15_000);
		expect(spy).toHaveBeenCalledTimes(1);

		resolveInitial(makeSnapshot({ name: "first" }));
		await vi.waitFor(() => expect(spy).toHaveBeenCalledTimes(2));
		await vi.waitFor(() => expect(store.manualRefreshing).toBe(false));
	});

	it("stops polling after dispose", async () => {
		vi.useFakeTimers();
		vi.spyOn(api, "fetchSnapshot").mockResolvedValue(
			makeSnapshot({ name: "overview" }),
		);
		make("overview");

		await vi.waitFor(() => expect(api.fetchSnapshot).toHaveBeenCalled());
		const calls = vi.mocked(api.fetchSnapshot).mock.calls.length;

		dispose?.();
		dispose = undefined;

		await vi.advanceTimersByTimeAsync(60_000);
		expect(vi.mocked(api.fetchSnapshot).mock.calls).toHaveLength(calls);
	});

	it("reloads when the reactive dashboard key changes", async () => {
		const spy = vi
			.spyOn(api, "fetchSnapshot")
			.mockImplementation(async (dashboard) =>
				makeSnapshot({ name: dashboard ?? "default" }),
			);
		let dashboard = $state<string | undefined>("overview");
		const { value: store, dispose: d } = root(() => {
			const s = new SnapshotStore();
			s.bind(() => dashboard);
			return s;
		});
		dispose = d;

		await vi.waitFor(() => expect(store.snapshot?.name).toBe("overview"));

		dashboard = "triage";
		await vi.waitFor(() => expect(store.snapshot?.name).toBe("triage"));
		expect(spy).toHaveBeenNthCalledWith(1, "overview");
		expect(spy).toHaveBeenNthCalledWith(2, "triage");
	});
});

type Listener = (event: MessageEvent) => void;

class FakeEventSource {
	static readonly CONNECTING = 0;
	static readonly OPEN = 1;
	static readonly CLOSED = 2;
	static readonly instances: FakeEventSource[] = [];

	url: string;
	readyState = FakeEventSource.CONNECTING;
	onerror: ((event: Event) => void) | null = null;
	closed = false;
	readonly #listeners = new Map<string, Listener[]>();

	constructor(url: string) {
		this.url = url;
		FakeEventSource.instances.push(this);
	}

	addEventListener(type: string, callback: Listener): void {
		const existing = this.#listeners.get(type) ?? [];
		existing.push(callback);
		this.#listeners.set(type, existing);
	}

	close(): void {
		this.closed = true;
		this.readyState = FakeEventSource.CLOSED;
	}

	emit(type: string, data: string): void {
		for (const callback of this.#listeners.get(type) ?? []) {
			callback({ data } as MessageEvent);
		}
	}

	emitConnectionError(readyState: number): void {
		this.readyState = readyState;
		this.onerror?.(new Event("error"));
	}
}

describe("SnapshotStore (SSE path)", () => {
	let dispose: (() => void) | undefined;

	function make(dashboard: string | undefined = undefined) {
		const { value, dispose: d } = root(() => {
			const s = new SnapshotStore();
			s.bind(() => dashboard);
			return s;
		});
		dispose = d;
		return value;
	}

	beforeEach(() => {
		FakeEventSource.instances.length = 0;
		vi.stubGlobal("EventSource", FakeEventSource);
		vi.spyOn(api, "fetchSnapshot").mockResolvedValue(
			makeSnapshot({ name: "initial" }),
		);
	});

	afterEach(() => {
		dispose?.();
		dispose = undefined;
		vi.unstubAllGlobals();
		vi.restoreAllMocks();
		vi.useRealTimers();
	});

	it("opens an EventSource with the dashboard-scoped URL", () => {
		make("overview");
		expect(FakeEventSource.instances).toHaveLength(1);
		expect(FakeEventSource.instances[0].url).toBe(
			"/api/v1/events?dashboard=overview",
		);
	});

	it("applies a pushed 'snapshot' event and clears loading", () => {
		const store = make();
		const source = FakeEventSource.instances[0];
		expect(source.url).toBe("/api/v1/events");

		source.emit("snapshot", JSON.stringify(makeSnapshot({ name: "live" })));
		expect(store.snapshot?.name).toBe("live");
		expect(store.error).toBeNull();
		expect(store.loading).toBe(false);
	});

	it("ignores malformed 'snapshot' frames", () => {
		const store = make();
		const source = FakeEventSource.instances[0];
		source.emit("snapshot", JSON.stringify(makeSnapshot({ name: "good" })));
		source.emit("snapshot", "not-json{");
		expect(store.snapshot?.name).toBe("good");
	});

	it("surfaces a server 'snapshot-error' event", () => {
		const store = make();
		const source = FakeEventSource.instances[0];
		source.emit(
			"snapshot-error",
			JSON.stringify({ detail: "config broken" }),
		);
		expect(store.error).toBe("config broken");
	});

	it("uses a generic message for a non-JSON 'snapshot-error'", () => {
		const store = make();
		FakeEventSource.instances[0].emit("snapshot-error", "boom");
		expect(store.error).toBe("Snapshot stream error");
	});

	it("uses a generic message when the error detail is empty", () => {
		const store = make();
		FakeEventSource.instances[0].emit(
			"snapshot-error",
			JSON.stringify({ detail: "" }),
		);
		expect(store.error).toBe("Snapshot stream error");
	});

	it("polls only after the connection is permanently CLOSED", async () => {
		vi.useFakeTimers();
		make();
		const source = FakeEventSource.instances[0];
		await vi.waitFor(() => expect(api.fetchSnapshot).toHaveBeenCalled());
		const callsAfterInitial = vi.mocked(api.fetchSnapshot).mock.calls.length;

		// Transient error (still connecting) must NOT start polling.
		source.emitConnectionError(FakeEventSource.CONNECTING);
		await vi.advanceTimersByTimeAsync(30_000);
		expect(vi.mocked(api.fetchSnapshot).mock.calls).toHaveLength(
			callsAfterInitial,
		);

		// A permanent close DOES start the polling fallback.
		source.emitConnectionError(FakeEventSource.CLOSED);
		await vi.advanceTimersByTimeAsync(15_000);
		expect(vi.mocked(api.fetchSnapshot).mock.calls.length).toBeGreaterThan(
			callsAfterInitial,
		);
	});

	it("does not start a second poll interval if CLOSED fires twice", async () => {
		vi.useFakeTimers();
		make();
		const source = FakeEventSource.instances[0];
		await vi.waitFor(() => expect(api.fetchSnapshot).toHaveBeenCalled());

		source.emitConnectionError(FakeEventSource.CLOSED);
		source.emitConnectionError(FakeEventSource.CLOSED);
		await vi.advanceTimersByTimeAsync(15_000);
		// Only one interval running: one auto poll fired in this window.
		const calls = vi.mocked(api.fetchSnapshot).mock.calls.length;
		await vi.advanceTimersByTimeAsync(15_000);
		expect(vi.mocked(api.fetchSnapshot).mock.calls).toHaveLength(calls + 1);
	});

	it("closes the EventSource and ignores late events after dispose", () => {
		const store = make();
		const source = FakeEventSource.instances[0];
		dispose?.();
		dispose = undefined;

		expect(source.closed).toBe(true);
		expect(() => {
			source.emit("snapshot", JSON.stringify(makeSnapshot({ name: "late" })));
			source.emit("snapshot-error", JSON.stringify({ detail: "late" }));
		}).not.toThrow();
		expect(store.snapshot?.name).not.toBe("late");
		expect(store.error).toBeNull();
	});

	it("does not start polling when a CLOSED error fires after dispose", async () => {
		vi.useFakeTimers();
		make();
		const source = FakeEventSource.instances[0];
		await vi.waitFor(() => expect(api.fetchSnapshot).toHaveBeenCalled());
		const callsBefore = vi.mocked(api.fetchSnapshot).mock.calls.length;

		dispose?.();
		dispose = undefined;
		source.emitConnectionError(FakeEventSource.CLOSED);
		await vi.advanceTimersByTimeAsync(30_000);
		expect(vi.mocked(api.fetchSnapshot).mock.calls).toHaveLength(callsBefore);
	});
});

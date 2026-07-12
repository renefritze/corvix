import { afterEach, describe, expect, it, vi } from "vitest";
import * as api from "../api";
import { makeSnapshot } from "../test/fixtures";
import { setPath } from "../test/http";
import { root } from "../test/runes.svelte";
import { DashboardsStore } from "./dashboards.svelte";
import { Router } from "./router.svelte";
import { SnapshotStore } from "./snapshot.svelte";

describe("DashboardsStore", () => {
	let dispose: (() => void) | undefined;
	let router: Router | undefined;

	function make(path: string) {
		setPath(path);
		vi.spyOn(api, "fetchSnapshot").mockImplementation(async (dashboard) =>
			makeSnapshot({
				name: dashboard ?? "overview",
				dashboard_names: ["overview", "triage"],
			}),
		);
		const { value, dispose: d } = root(() => {
			router = new Router();
			const snapshot = new SnapshotStore();
			const store = new DashboardsStore(router, snapshot);
			store.bind();
			return store;
		});
		dispose = d;
		return value;
	}

	afterEach(() => {
		dispose?.();
		dispose = undefined;
		router?.destroy();
		router = undefined;
		vi.restoreAllMocks();
		vi.useRealTimers();
	});

	it("defaults to the first dashboard and normalizes the URL (replace)", async () => {
		const store = make("/");
		// Captured after the synchronous setPath; normalization is async and has
		// not run yet (the name list is still empty during the initial flush).
		const lengthBefore = globalThis.history.length;

		await vi.waitFor(() =>
			expect(globalThis.location.pathname).toBe("/dashboards/overview"),
		);
		expect(store.currentDashboard).toBe("overview");
		expect(store.dashboardNames).toEqual(["overview", "triage"]);
		// Normalization replaces history, so no new entry is added.
		expect(globalThis.history.length).toBe(lengthBefore);
		// The default snapshot is fetched once with an undefined key (no refetch
		// after normalizing "/" -> "/dashboards/overview").
		expect(api.fetchSnapshot).toHaveBeenCalledTimes(1);
		expect(api.fetchSnapshot).toHaveBeenCalledWith(undefined);
	});

	it("falls back to the default dashboard for an unknown URL name", async () => {
		const store = make("/dashboards/unknown");

		await vi.waitFor(() =>
			expect(globalThis.location.pathname).toBe("/dashboards/overview"),
		);
		expect(store.currentDashboard).toBe("overview");
	});

	it("reads the dashboard name from the route and preserves the query", async () => {
		const store = make("/dashboards/triage?unread=unread");

		await vi.waitFor(() => expect(store.currentDashboard).toBe("triage"));
		expect(globalThis.location.pathname).toBe("/dashboards/triage");
		expect(globalThis.location.search).toBe("?unread=unread");
		expect(store.fetchKey).toBe("triage");
	});

	it("setDashboard pushes a new history entry", async () => {
		const store = make("/");
		await vi.waitFor(() =>
			expect(globalThis.location.pathname).toBe("/dashboards/overview"),
		);

		const lengthBefore = globalThis.history.length;
		store.setDashboard("triage");

		await vi.waitFor(() =>
			expect(globalThis.location.pathname).toBe("/dashboards/triage"),
		);
		expect(store.currentDashboard).toBe("triage");
		expect(globalThis.history.length).toBe(lengthBefore + 1);
	});

	it("exposes an empty name list before the snapshot arrives", () => {
		let resolve!: (p: ReturnType<typeof makeSnapshot>) => void;
		vi.spyOn(api, "fetchSnapshot").mockImplementation(
			() => new Promise((r) => (resolve = r)),
		);
		setPath("/");
		const { value: store, dispose: d } = root(() => {
			router = new Router();
			const snapshot = new SnapshotStore();
			const s = new DashboardsStore(router, snapshot);
			s.bind();
			return s;
		});
		dispose = d;

		expect(store.dashboardNames).toEqual([]);
		expect(store.currentDashboard).toBeNull();
		resolve(makeSnapshot());
	});

	it("fetchKey is undefined for the default dashboard", async () => {
		const store = make("/");
		await vi.waitFor(() =>
			expect(globalThis.location.pathname).toBe("/dashboards/overview"),
		);
		// Resolved default -> key stays undefined so no refetch on normalization.
		expect(store.fetchKey).toBeUndefined();
	});
});

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { flushSync, root } from "../test/runes.svelte";
import { ColumnResizeStore } from "./columnResize.svelte";

const STORAGE_KEY = "corvix.table.columnWidths.v2";
const LEGACY_KEY = "corvix.table.columnWidths";

describe("ColumnResizeStore", () => {
	let dispose: (() => void) | undefined;

	function make() {
		const { value, dispose: d } = root(() => {
			const s = new ColumnResizeStore();
			s.bind();
			return s;
		});
		dispose = d;
		return value;
	}

	function moveMouse(clientX: number) {
		globalThis.window.dispatchEvent(new MouseEvent("mousemove", { clientX }));
	}

	function releaseMouse() {
		globalThis.window.dispatchEvent(new MouseEvent("mouseup"));
	}

	function stored(): Record<string, number> {
		return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}");
	}

	beforeEach(() => {
		localStorage.clear();
		document.body.classList.remove("col-resizing");
	});

	afterEach(() => {
		dispose?.();
		dispose = undefined;
	});

	it("uses default widths when storage is empty", () => {
		const store = make();
		expect(store.widths.repository).toBe(185);
		expect(store.widths.score).toBe(75);
	});

	it("reads saved widths from the versioned key", () => {
		localStorage.setItem(STORAGE_KEY, JSON.stringify({ repository: 200 }));
		const store = make();
		expect(store.widths.repository).toBe(200);
	});

	it("migrates from the legacy unversioned key and removes it", () => {
		localStorage.setItem(LEGACY_KEY, JSON.stringify({ repository: 240 }));
		const store = make();

		expect(store.widths.repository).toBe(240);
		flushSync();
		expect(localStorage.getItem(LEGACY_KEY)).toBeNull();
		expect(stored().repository).toBe(240);
	});

	it("prefers the versioned key over the legacy key", () => {
		localStorage.setItem(LEGACY_KEY, JSON.stringify({ repository: 240 }));
		localStorage.setItem(STORAGE_KEY, JSON.stringify({ repository: 200 }));
		const store = make();
		expect(store.widths.repository).toBe(200);
	});

	it("clamps too-small stored widths to the minimum", () => {
		localStorage.setItem(LEGACY_KEY, JSON.stringify({ repository: 10 }));
		const store = make();
		expect(store.widths.repository).toBe(120);
	});

	it("normalizes partially invalid stored widths", () => {
		localStorage.setItem(
			LEGACY_KEY,
			JSON.stringify({
				repository: "nope",
				subject_type: 20,
				reason: 210,
				score: null,
				updated_at: 90,
			}),
		);
		const store = make();
		expect(store.widths.repository).toBe(185); // non-finite -> default
		expect(store.widths.subject_type).toBe(90); // 20 clamped to min 90
		expect(store.widths.reason).toBe(210); // valid, above min
		expect(store.widths.score).toBe(64); // Number(null)===0 -> clamped to min 64
		expect(store.widths.updated_at).toBe(96); // 90 clamped to min 96
	});

	it("falls back to defaults from malformed JSON", () => {
		localStorage.setItem(LEGACY_KEY, "{broken");
		const store = make();
		expect(store.widths.repository).toBe(185);
	});

	it("falls back to defaults when getItem throws on init", () => {
		vi.spyOn(globalThis.window.localStorage, "getItem").mockImplementation(
			() => {
				throw new Error("SecurityError");
			},
		);
		const store = make();
		expect(store.widths.repository).toBe(185);
	});

	it("resizes a column via drag and clamps at the minimum", () => {
		const store = make();
		store.startResize("repository", 100);
		expect(document.body.classList.contains("col-resizing")).toBe(true);

		moveMouse(150);
		expect(store.widths.repository).toBe(235);

		// Overshoot far below the minimum clamps to MIN (120).
		moveMouse(-10_000);
		expect(store.widths.repository).toBe(120);

		releaseMouse();
		expect(document.body.classList.contains("col-resizing")).toBe(false);
		// Listener removed: subsequent moves no longer resize.
		moveMouse(300);
		expect(store.widths.repository).toBe(120);
	});

	it("ignores mousemove before a resize starts", () => {
		const store = make();
		moveMouse(999);
		expect(store.widths.repository).toBe(185);
	});

	it("does not change width when the pointer stays put", () => {
		const store = make();
		store.startResize("repository", 100);
		moveMouse(100);
		expect(store.widths.repository).toBe(185);
		store.stopResize();
	});

	it("restarting a resize tears down the previous drag first", () => {
		const store = make();
		store.startResize("repository", 100);
		store.startResize("score", 50);
		moveMouse(80);
		// Only the score column should move now.
		expect(store.widths.repository).toBe(185);
		expect(store.widths.score).toBe(75 + 30);
		store.stopResize();
	});

	it("resets a single column width to its default", () => {
		const store = make();
		store.startResize("repository", 100);
		moveMouse(160);
		expect(store.widths.repository).toBe(245);
		releaseMouse();

		store.resetColumnWidth("repository");
		expect(store.widths.repository).toBe(185);
	});

	it("resets every column width", () => {
		const store = make();
		store.startResize("repository", 100);
		moveMouse(160);
		releaseMouse();

		store.resetLayout();
		expect(store.widths.repository).toBe(185);
		expect(store.widths.score).toBe(75);
	});

	it("persists widths under the versioned key on change", () => {
		const store = make();
		store.startResize("repository", 100);
		moveMouse(150);
		releaseMouse();
		flushSync();
		expect(stored().repository).toBe(235);
	});

	it("swallows localStorage write errors while resizing", () => {
		vi.spyOn(globalThis.window.localStorage, "setItem").mockImplementation(
			() => {
				throw new Error("quota");
			},
		);
		const store = make();
		store.startResize("repository", 100);
		expect(() => {
			moveMouse(150);
			flushSync();
		}).not.toThrow();
		expect(store.widths.repository).toBe(235);
		store.stopResize();
	});

	it("removes stale older-version keys on mount but keeps unrelated ones", () => {
		localStorage.setItem(LEGACY_KEY, JSON.stringify({ repository: 200 }));
		localStorage.setItem(
			"corvix.table.columnWidths.v1",
			JSON.stringify({ repository: 210 }),
		);
		localStorage.setItem("corvix.unrelated.key", "keep-me");

		make();
		flushSync();

		expect(localStorage.getItem(LEGACY_KEY)).toBeNull();
		expect(localStorage.getItem("corvix.table.columnWidths.v1")).toBeNull();
		expect(localStorage.getItem("corvix.unrelated.key")).toBe("keep-me");
	});

	it("no-ops DOM and storage access when window/document are undefined", () => {
		vi.stubGlobal("window", undefined);
		vi.stubGlobal("document", undefined);
		try {
			// Constructor skips the localStorage read (keeps defaults).
			const store = new ColumnResizeStore();
			expect(store.widths.repository).toBe(185);
			// startResize / stopResize skip their document + window branches.
			expect(() => {
				store.startResize("repository", 100);
				store.stopResize();
			}).not.toThrow();
		} finally {
			vi.unstubAllGlobals();
		}
	});

	it("bind persistence no-ops when window is undefined", () => {
		vi.stubGlobal("window", undefined);
		try {
			const { dispose: d } = root(() => {
				const s = new ColumnResizeStore();
				s.bind();
				return s;
			});
			d();
		} finally {
			vi.unstubAllGlobals();
		}
	});

	it("stops an in-flight drag on dispose", () => {
		const store = make();
		store.startResize("repository", 100);
		expect(document.body.classList.contains("col-resizing")).toBe(true);

		dispose?.();
		dispose = undefined;
		expect(document.body.classList.contains("col-resizing")).toBe(false);
	});
});

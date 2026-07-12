import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ThemeStore } from "./theme.svelte";

function stubMatchMedia(matches: boolean): void {
	vi.spyOn(globalThis, "matchMedia").mockReturnValue({
		matches,
		media: "",
		addEventListener: vi.fn(),
		removeEventListener: vi.fn(),
	} as unknown as MediaQueryList);
}

describe("ThemeStore", () => {
	let store: ThemeStore | undefined;

	// The setup's restoreAllMocks does not revert a matchMedia override, so
	// reinstall the default (matches: false) before each test.
	beforeEach(() => stubMatchMedia(false));

	afterEach(() => {
		store?.destroy();
		store = undefined;
	});

	it("defaults to system when nothing is stored", () => {
		store = new ThemeStore();
		expect(store.preference).toBe("system");
		// matchMedia is mocked with matches: false, so system resolves to light.
		expect(store.resolved).toBe("light");
		expect(document.documentElement.dataset.theme).toBe("light");
	});

	it("reads a stored explicit preference", () => {
		localStorage.setItem("corvix.theme", "dark");
		store = new ThemeStore();
		expect(store.preference).toBe("dark");
		expect(store.resolved).toBe("dark");
	});

	it("ignores a malformed stored value", () => {
		localStorage.setItem("corvix.theme", "chartreuse");
		store = new ThemeStore();
		expect(store.preference).toBe("system");
	});

	it("resolves system to dark when the media query matches", () => {
		stubMatchMedia(true);
		store = new ThemeStore();
		expect(store.resolved).toBe("dark");
	});

	it("persists an explicit preference and mirrors it to the document", () => {
		store = new ThemeStore();
		store.setPreference("dark");
		expect(localStorage.getItem("corvix.theme")).toBe("dark");
		expect(document.documentElement.dataset.theme).toBe("dark");
	});

	it("removes the stored key when set back to system", () => {
		localStorage.setItem("corvix.theme", "dark");
		store = new ThemeStore();
		store.setPreference("system");
		expect(localStorage.getItem("corvix.theme")).toBeNull();
		expect(store.resolved).toBe("light");
	});

	it("toggles between the two concrete themes", () => {
		store = new ThemeStore();
		store.setPreference("dark");
		store.toggle();
		expect(store.preference).toBe("light");
		store.toggle();
		expect(store.preference).toBe("dark");
	});

	it("cycles system -> light -> dark -> system", () => {
		store = new ThemeStore();
		expect(store.preference).toBe("system");
		store.cycle();
		expect(store.preference).toBe("light");
		store.cycle();
		expect(store.preference).toBe("dark");
		store.cycle();
		expect(store.preference).toBe("system");
	});

	it("reacts to a system color-scheme change", () => {
		let handler: ((event: MediaQueryListEvent) => void) | undefined;
		const removeEventListener = vi.fn();
		vi.spyOn(globalThis, "matchMedia").mockReturnValue({
			matches: false,
			media: "",
			addEventListener: (_: string, cb: (e: MediaQueryListEvent) => void) => {
				handler = cb;
			},
			removeEventListener,
		} as unknown as MediaQueryList);
		store = new ThemeStore();
		expect(store.resolved).toBe("light");
		handler?.({ matches: true } as MediaQueryListEvent);
		expect(store.resolved).toBe("dark");
		expect(document.documentElement.dataset.theme).toBe("dark");

		store.destroy();
		store = undefined;
		expect(removeEventListener).toHaveBeenCalled();
	});
});

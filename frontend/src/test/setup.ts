import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/preact";
import { afterEach, vi } from "vitest";

class ResizeObserverMock {
	observe = vi.fn();
	unobserve = vi.fn();
	disconnect = vi.fn();
}

Object.defineProperty(globalThis, "ResizeObserver", {
	value: ResizeObserverMock,
	writable: true,
});

Object.defineProperty(globalThis, "matchMedia", {
	writable: true,
	value: vi.fn().mockImplementation((query: string) => ({
		matches: false,
		media: query,
		onchange: null,
		addListener: vi.fn(),
		removeListener: vi.fn(),
		addEventListener: vi.fn(),
		removeEventListener: vi.fn(),
		dispatchEvent: vi.fn(),
	})),
});

if (typeof globalThis.window !== "undefined") {
	Object.defineProperty(globalThis.window, "matchMedia", {
		writable: true,
		value: globalThis.matchMedia,
	});
}

Object.defineProperty(globalThis, "open", {
	writable: true,
	value: vi.fn(),
});

Object.defineProperty(window.navigator, "clipboard", {
	value: { writeText: vi.fn() },
	configurable: true,
});

afterEach(() => {
	cleanup();
	localStorage.clear();
	vi.clearAllMocks();
	vi.restoreAllMocks();
	vi.useRealTimers();
});

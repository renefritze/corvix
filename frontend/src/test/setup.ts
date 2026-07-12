import "@testing-library/jest-dom/vitest";
import { afterEach, vi } from "vitest";

// @testing-library/svelte auto-cleanup is registered by the svelteTesting()
// Vite plugin (see vite.config.ts test mode), so no manual cleanup import is
// needed here — only the environment globals the suites depend on.

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

if (globalThis.window !== undefined) {
	Object.defineProperty(globalThis.window, "matchMedia", {
		writable: true,
		value: globalThis.matchMedia,
	});
}

Object.defineProperty(globalThis, "open", {
	writable: true,
	value: vi.fn(),
});

Object.defineProperty(globalThis, "requestAnimationFrame", {
	writable: true,
	value: (callback: FrameRequestCallback) =>
		setTimeout(() => callback(performance.now()), 0),
});

Object.defineProperty(globalThis, "cancelAnimationFrame", {
	writable: true,
	value: (id: ReturnType<typeof setTimeout>) => clearTimeout(id),
});

if (globalThis.window !== undefined) {
	Object.defineProperty(globalThis.window, "open", {
		writable: true,
		value: globalThis.open,
	});

	Object.defineProperty(globalThis.window, "requestAnimationFrame", {
		writable: true,
		value: globalThis.requestAnimationFrame,
	});

	Object.defineProperty(globalThis.window, "cancelAnimationFrame", {
		writable: true,
		value: globalThis.cancelAnimationFrame,
	});
}

Object.defineProperty(globalThis.navigator, "clipboard", {
	value: { writeText: vi.fn() },
	configurable: true,
});

// jsdom does not implement the Web Animations API. Svelte 5's built-in
// transitions (fly/fade on toasts) call `element.animate`; without this stub
// the call throws and bubbles into the nearest <svelte:boundary>. The stub
// resolves immediately (fires onfinish) so outro transitions still remove nodes.
if (typeof Element !== "undefined" && !Element.prototype.animate) {
	Object.defineProperty(Element.prototype, "animate", {
		writable: true,
		configurable: true,
		value: function animate() {
			const animation = {
				onfinish: null as null | (() => void),
				oncancel: null as null | (() => void),
				cancel() {},
				finish() {},
				play() {},
				pause() {},
				finished: Promise.resolve(),
			};
			queueMicrotask(() => animation.onfinish?.());
			return animation as unknown as Animation;
		},
	});
}

afterEach(() => {
	localStorage.clear();
	sessionStorage.clear();
	vi.clearAllMocks();
	vi.restoreAllMocks();
	vi.useRealTimers();
});

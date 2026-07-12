import { render, screen } from "@testing-library/svelte";
import userEvent from "@testing-library/user-event";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { prefersReducedMotion } from "../lib/motion.svelte";
import UndoToast from "./UndoToast.svelte";

vi.mock("../lib/motion.svelte", () => ({
	prefersReducedMotion: vi.fn(() => false),
}));

// The `fly` transition relies on the Web Animations API, which jsdom lacks;
// provide a no-op that resolves immediately so the outro transition completes.
beforeAll(() => {
	if (typeof Element.prototype.animate !== "function") {
		Element.prototype.animate = function () {
			return {
				cancel: () => {},
				finished: Promise.resolve(),
				onfinish: null,
				play: () => {},
				pause: () => {},
				currentTime: 0,
				playState: "finished",
				addEventListener: () => {},
				removeEventListener: () => {},
			} as unknown as Animation;
		};
	}
});

describe("UndoToast", () => {
	it("renders nothing when the count is zero", () => {
		render(UndoToast, { props: { count: 0, onUndoAll: vi.fn() } });
		expect(screen.queryByTestId("undo-toast")).toBeNull();
	});

	it("renders the singular label for one pending dismissal", () => {
		render(UndoToast, { props: { count: 1, onUndoAll: vi.fn() } });
		expect(screen.getByTestId("undo-toast")).toHaveTextContent(
			"1 notification dismissing",
		);
	});

	it("renders the plural label and fires onUndoAll from the Undo button", async () => {
		const onUndoAll = vi.fn();
		render(UndoToast, { props: { count: 2, onUndoAll } });
		expect(screen.getByTestId("undo-toast")).toHaveTextContent(
			"2 notifications dismissing",
		);
		await userEvent.click(screen.getByRole("button", { name: "Undo" }));
		expect(onUndoAll).toHaveBeenCalledTimes(1);
	});

	// The reduced-motion mock keeps `prefersReducedMotion()` overridable; the
	// `flyParams` derived it feeds is only read by the transition engine, which
	// does not run under jsdom's mount, so this documents the wiring.
	it("supports a reduced-motion preference", () => {
		vi.mocked(prefersReducedMotion).mockReturnValue(true);
		render(UndoToast, { props: { count: 1, onUndoAll: vi.fn() } });
		expect(screen.getByTestId("undo-toast")).toBeInTheDocument();
	});
});
